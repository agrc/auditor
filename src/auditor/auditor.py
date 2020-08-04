"""
auditor.py

See cli.py for usage
"""

import datetime

from pathlib import Path
from time import sleep
from urllib.error import HTTPError

import pandas as pd

import arcgis
import arcpy

from . import checks, fixes, credentials


def retry(worker, verbose=True, tries=1):
    """
    Helper function to retry a function or method with an incremental wait time.
    Useful for methods reliant on unreliable network connections.
    """
    max_tries = 3
    delay = 2  #: in seconds

    try:
        return worker()

    #: Retry on HTTPErrors (ie, bad connections to AGOL)
    except Exception as error:
        if tries <= max_tries:
            wait_time = delay**tries
            if verbose:
                print(f'Exception "{error}" thrown on "{worker}". Retrying after {wait_time} seconds...')
            sleep(wait_time)
            retry(worker, verbose, tries + 1)
        else:
            raise error


class Auditor:
    """
    An object representing an AGOL/Portal organization and information about
    its items. Contains methods for checking and fixing various elements of
    each item's settings (name, tags, group, etc).

    This class contains data and methods specific to all items in the org.
    Specifics to each item should go in the ItemChecker or ItemFixer classes.
    """

    #: Tags or words that should be uppercased, saved as lower to check against
    uppercased_tags = [
        '2g', '3g', '4g', 'agol', 'agrc', 'aog', 'at&t', 'atv', 'blm', 'brat', 'caf', 'cdl', 'dabc', 'daq', 'dem',
        'dfcm', 'dfirm', 'dnr', 'dogm', 'dot', 'dsl', 'dsm', 'dtm', 'dwq', 'e911', 'ems', 'epa', 'fae', 'fcc', 'fema',
        'gcdb', 'gis', 'gnis', 'hava', 'huc', 'lir', 'lrs', 'lte', 'luca', 'mrrc', 'nca', 'ng911', 'ngda', 'nox',
        'npsbn', 'ntia', 'nwi', 'osa', 'pli', 'plss', 'pm10', 'ppm', 'psap', 'sao', 'sbdc', 'sbi', 'sgid', 'sitla',
        'sligp', 'trax', 'uca', 'udot', 'ugs', 'uhp', 'uic', 'uipa', 'us', 'usao', 'usdw', 'usfs', 'usfws', 'usps',
        'ustc', 'ut', 'uta', 'utsc', 'vcp', 'vista', 'voc', 'wbd', 'wre'
    ]

    #: Articles that should be left lowercase.
    articles = ['a', 'an', 'the', 'of', 'is', 'in']

    #: Tags that should be deleted, saved as lower to check against
    tags_to_delete = [
        '.sd',
        'service definition',
        'required: common-use word or phrase used to describe the subject of the data set',
        '002',
        'required: common-use word or phrase used to describe the subject of the data set.',
    ]

    #: Notes for static and shelved descriptions
    static_note = (
        '<i><b>NOTE</b>: This dataset holds \'static\' data that we don\'t expect to change. We have removed it from '
        'the SDE database and placed it in ArcGIS Online, but it is still considered part of the SGID and shared on '
        'opendata.gis.utah.gov.</i>'
    )

    shelved_note = (
        '<i><b>NOTE</b>: This dataset is an older dataset that we have removed from the SGID and \'shelved\' in ArcGIS '
        'Online. There may (or may not) be a newer vintage of this dataset in the SGID.</i>'
    )

    def __init__(self, verbose=False):
        """
        Create an arcgis.gis.GIS object using the user, portal, and password set in credentials.py. Automatically
        create a list of all the Feature Service objects in the user's folders and a dictionary of each item's folder
        based on itemid. Read SDE and AGOL metatables into a dictionary based on the itemid.
        """

        #: Metatables
        self.metatable = credentials.METATABLE
        self.agol_table = credentials.AGOL_TABLE

        #: A list of log entries, format TBD
        self.report_dict = {}

        #: A list of feature service item objects generated by trawling all of
        #: the user's folders
        self.feature_service_items = []

        #: A dictionary of items and their folder
        self.itemid_and_folder = {}

        #: A dictionary of the metatable records, indexed by the metatable's itemid
        #: values: {item_id: [table_sgid_name, table_agol_name, table_category, table_authoritative]}
        self.metatable_dict = {}

        #: A dictionary of groups and their ID:
        self.groups_dict = {}

        #: Simplified count of fixes for logging:
        self.fix_counts = {}

        self.verbose = verbose

        self.username = credentials.USERNAME

        self.metadata_xml_template = credentials.XML_TEMPLATE

        #: TODO: Wrap in a method, call via retry()
        try:
            self.gis = arcgis.gis.GIS(credentials.ORG, credentials.USERNAME, credentials.PASSWORD)

            #: Make sure ArcGIS Pro is properly logged in
            arcpy.SignInToPortal(arcpy.GetActivePortalURL(), credentials.USERNAME, credentials.PASSWORD)

            user_item = self.gis.users.me  # pylint: disable=no-member

            #: Build list of folders. 'None' gives us the root folder.
            if self.verbose:
                print(f'Getting {self.username}\'s folders...')
            folders = [None]
            for folder in user_item.folders:
                folders.append(folder['title'])

            #: Get info for every item in every folder
            if self.verbose:
                print('Getting item objects...')
            for folder in folders:
                for item in user_item.items(folder, 1000):
                    if item.type == 'Feature Service':
                        self.feature_service_items.append(item)
                        self.itemid_and_folder[item.itemid] = folder

            #: Read the metatable into memory as a dictionary based on itemid.
            #: Getting this once so we don't have to re-read every iteration
            if self.verbose:
                print('Getting metatable info...')
            duplicate_keys = []

            meta_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'Authoritative']
            meta_dupes = self.read_metatable(self.metatable, meta_fields)

            agol_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'CATEGORY']
            agol_dupes = self.read_metatable(self.agol_table, agol_fields)

            if meta_dupes:
                duplicate_keys.append(meta_dupes)
            if agol_dupes:
                duplicate_keys.append(agol_dupes)

            if duplicate_keys:
                raise RuntimeError(f'Duplicate AGOL item IDs found in metatables: {duplicate_keys}')

            #: Get the groups
            if self.verbose:
                print('Getting groups...')
            groups = self.gis.groups.search('title:*')  # pylint: disable=no-member
            self.groups_dict = {g.title: g.id for g in groups}

        except HTTPError:
            print(f'Connection error, probably for connection with {credentials.ORG}')
            raise

    def read_metatable(self, table, fields):
        """
        Read metatable 'table' into self.metatable_dict.

        Returns: list of any duplicate AGOL item ids found
        """

        duplicate_keys = []

        with arcpy.da.SearchCursor(table, fields) as meta_cursor:  # pylint: disable=no-member
            for row in meta_cursor:

                if fields[-1] == 'Authoritative':  #: AGOLItems table's last field is "Authoritative"
                    table_sgid_name, table_agol_itemid, table_agol_name, table_authoritative = row
                    table_category = 'SGID'

                else:  #: Shelved table hosted in AGOL's last field is "CATEGORY"
                    table_sgid_name, table_agol_itemid, table_agol_name, table_category = row
                    table_authoritative = 'n'

                if table_agol_itemid:  #: Don't evaluate null itemids
                    if table_agol_itemid not in self.metatable_dict:
                        self.metatable_dict[table_agol_itemid] = [
                            table_sgid_name, table_agol_name, table_category, table_authoritative
                        ]
                    else:
                        duplicate_keys.append(table_agol_itemid)

        return duplicate_keys

    def check_items(self, report_dir=None):
        """
        Instantiates an ItemChecker for each item and manually runs the
        specified check methods. The results of the checks are saved in
        self.report_dict, which can be used to guide the fixes. Exports the
        final self.report_dict to a csv named checks_yyyy-mm-dd.csv in
        'report_dir', if specified.
        """

        counter = 0
        try:
            for item in self.feature_service_items:

                counter += 1

                if self.verbose:
                    print(f'Checking {item.title} ({counter} of {len(self.feature_service_items)})...')

                itemid = item.itemid

                #: Initialize empty dictionary for this item
                self.report_dict[itemid] = {}

                checker = checks.ItemChecker(item, self.metatable_dict)
                retry(lambda: checker.setup(credentials.DB))  # pylint: disable=W0640

                #: TODO: add each method and it's args to a list, then iterate through the list (DRY)

                #: Run the checks on this item
                retry(lambda: checker.tags_check(self.tags_to_delete, self.uppercased_tags, self.articles))  # pylint: disable=W0640
                retry(checker.title_check)
                retry(lambda: checker.folder_check(self.itemid_and_folder))  # pylint: disable=W0640
                retry(checker.groups_check)
                retry(checker.downloads_check)
                retry(checker.delete_protection_check)
                retry(checker.metadata_check)
                retry(lambda: checker.description_note_check(self.static_note, self.shelved_note))  # pylint: disable=W0640
                checker.thumbnail_check(credentials.THUMBNAIL_DIR)
                retry(checker.authoritative_check)
                retry(checker.visibility_check)

                #: Add results to the report
                self.report_dict[itemid].update(checker.results_dict)

        finally:
            #: Convert dict to pandas df for easy writing
            if report_dir:
                report_path = Path(report_dir, f'checks_{datetime.date.today()}.csv')
                report_df = pd.DataFrame(self.report_dict).T
                report_df.to_csv(report_path)

    def fix_items(self, report_dir=None):
        """
        Instantiates an ItemFixer for each item and manually runs the specified
        fix methods using data in self.report_dict. Appends results to
        self.report_dict and writes the whole dictionary to a csv named
        checks_yyyy-mm-dd.csv in 'report_path' (if specified).
        """

        counter = 0
        try:
            for itemid in self.report_dict:

                counter += 1

                item = self.gis.content.get(itemid)  # pylint: disable=no-member
                item_report = self.report_dict[itemid]

                if self.verbose:
                    print(f'Evaluating report for fixes on {item.title} ({counter} of {len(self.report_dict)})...')

                fixer = fixes.ItemFixer(item, item_report)

                #: TODO: add each method and it's args to a list, then iterate through the list (DRY)

                #: Do the metadata fix first so that the tags, title, and
                #: description fixes later on aren't overwritten by the metadata
                #: upload.
                retry(lambda: fixer.metadata_fix(self.metadata_xml_template))  # pylint: disable=W0640
                retry(fixer.tags_fix)
                retry(fixer.title_fix)
                retry(lambda: fixer.group_fix(self.groups_dict))  # pylint: disable=W0640
                retry(fixer.folder_fix)
                retry(fixer.delete_protection_fix)
                retry(fixer.downloads_fix)
                retry(lambda: fixer.description_note_fix(self.static_note, self.shelved_note))  # pylint: disable=W0640
                retry(fixer.thumbnail_fix)
                retry(fixer.authoritative_fix)
                retry(fixer.visibility_fix)

                update_status_keys = [
                    'metadata_result', 'tags_result', 'title_result', 'groups_result', 'folder_result',
                    'delete_protection_result', 'downloads_result', 'description_note_result', 'thumbnail_result',
                    'authoritative_result', 'visibility_result'
                ]

                for status in update_status_keys:
                    if 'No update needed for' not in item_report[status]:
                        #: Increment fixed item summary statistic
                        if status in self.fix_counts:
                            self.fix_counts[status] += 1
                        else:
                            self.fix_counts[status] = 1
                        #: Log actual fixes
                        if self.verbose:
                            print(f'\t{item_report[status]}')

        except KeyboardInterrupt:
            print('Interrupted by Ctrl-c')
            raise

        finally:
            #: Convert dict to pandas df for easy writing
            if report_dir:
                report_path = Path(report_dir, f'fixes_{datetime.date.today()}.csv')
                report_df = pd.DataFrame(self.report_dict).T
                report_df.to_csv(report_path)

            if self.fix_counts:
                for fix_type in self.fix_counts:
                    # fix = fix_type.split('_')[0]  #: will be used later to ignore certain fix counts
                    print(f'{self.fix_counts[fix_type]} items updated for {fix_type}')
