"""
auditor.py

See cli.py for usage
"""

import datetime
import logging
import uuid

from pathlib import Path
from time import sleep
from urllib.error import HTTPError

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


#: TODO: Modify structure so each check/fix method returns its values directly rather than putting them inside
#: the dictionary, and then log results at the end of each for item in collection iteration.
def log_report(report_dict, report_file, separator='|', rotate_count=18):
    """
    Logs a nested dictionary to a rotating csv file via the logging module.

    report_dict:    Nested dictionary in the form of {Unique ID: {field1:data, field2:data, field3:data},
                    Unique ID: {field1:data, field2:data, field3:data}, ... }.
    report_file:    Base log file name, as a string. Automatically rotated by a logging RotatingFileHandler on each
                    call.
    separator:      The character used as a csv delimiter. Default to '|' to avoid common conflicts with text data.
    rotate_count:   The number of files to save before RotatingFileHandler deletes old reports. Defaults to 2.5 weeks.

    """
    #: Set up a rotating file handler for the report log
    report_path = Path(report_file)
    report_logger = logging.getLogger('audit_report')
    report_handler = logging.handlers.RotatingFileHandler(report_path, backupCount=rotate_count)
    report_handler.doRollover()  #: Rotate the log on each run
    report_handler.setLevel(logging.DEBUG)
    report_logger.addHandler(report_handler)
    report_logger.setLevel(logging.DEBUG)

    #: Log date
    timestamp = datetime.datetime.now()
    report_logger.info(timestamp)

    #: Get the column values from the keys of nested dict of the first item and log as csv header
    columns = list(next(iter(report_dict.items()))[1].keys())
    header = f'agol_id{separator}{separator.join(columns)}'
    report_logger.info(header)

    #: iterate through report_dict, using the columns generated above as keys of each nested dict to
    #: ensure the order stays the same for each row.
    for agol_id, item_report_dict in report_dict.items():
        item_list = [agol_id]
        item_list.extend([str(item_report_dict[col]) for col in columns])
        report_logger.info(separator.join(item_list))


class Metatable:

    def __init__(self):
        #: A dictionary of the metatable records, indexed by the metatable's itemid
        #: values: {item_id: [table_sgid_name, table_agol_name, table_category, table_authoritative]}
        self.metatable_dict = {}
        self.duplicate_keys = []

    def read_metatable(self, table, fields):
        """
        Read metatable 'table' into self.metatable_dict.

        Returns: list of any duplicate AGOL item ids found
        """

        with arcpy.da.SearchCursor(table, fields) as meta_cursor:
            for row in meta_cursor:

                if fields[-1] == 'Authoritative':  #: SGID's AGOLItems table's last field is "Authoritative"
                    table_sgid_name, table_agol_itemid, table_agol_name, table_authoritative = row
                    table_category = 'SGID'

                else:  #: Shelved table hosted in AGOL's last field is "CATEGORY"
                    table_sgid_name, table_agol_itemid, table_agol_name, table_category = row
                    table_authoritative = 'n'

                #: Item IDs are UUIDs. If we can't parse the item id listed in the table, it means the layer is not
                #: in AGOL and this row should be skipped (catches both magic words and empty entries)
                try:
                    uuid.UUID(table_agol_itemid)
                except (AttributeError, ValueError, TypeError):
                    continue

                if table_agol_itemid not in self.metatable_dict:
                    self.metatable_dict[table_agol_itemid] = [
                        table_sgid_name, table_agol_name, table_category, table_authoritative
                    ]
                else:
                    self.duplicate_keys.append(table_agol_itemid)


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

    def __init__(self, log, verbose=False, item_ids=None):
        """
        Create an arcgis.gis.GIS object using the user, portal, and password set in credentials.py. Automatically
        create a list of all the Feature Service objects in the user's folders and a dictionary of each item's folder
        based on itemid. Read SDE and AGOL metatables into a dictionary based on the itemid.
        """

        #: Metatables
        self.sgid_table = credentials.METATABLE
        self.agol_table = credentials.AGOL_TABLE

        #: A nested dictionary of log entries whose outer key is the the item_id. The inner dictionary for each
        #: item_id is built first by the checker with _fix, _old, and _new entries (which are assigned empty
        #: strings if not applicable). The fixer then appends the _result entry to the inner dictionary.
        #: {item_id: {<topic>_fix:'', <topic>_old:'', <topic>_new:''...<topic>_result:''}, ...}
        self.report_dict = {}

        #: A list of feature service items to audit
        self.items_to_check = []

        #: Hosted Feature Service items in the AGOL org
        self.agol_items = []

        #: A dictionary of items and their folder
        self.itemid_and_folder = {}

        #: A dictionary of the metatable records, indexed by the metatable's itemid
        #: values: {item_id: [table_sgid_name, table_agol_name, table_category, table_authoritative]}
        # self.metatable_dict = {}

        #: A dictionary of groups and their ID:
        self.groups_dict = {}

        #: Simplified count of fixes for logging:
        self.fix_counts = {}

        #: GIS object
        self.gis = None

        #: Metatable object holding info used in checks
        self.metatable = None

        self.verbose = verbose

        self.username = credentials.USERNAME

        self.metadata_xml_template = credentials.XML_TEMPLATE

        self.log = log

        self.item_ids = item_ids

        self.setup()

    #: TODO: Wrap in a method, call via retry()
    def setup(self):

        self.log.info(f'Logging into {credentials.ORG} as {credentials.USERNAME}')

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
                    self.agol_items.append(item)
                    self.itemid_and_folder[item.itemid] = folder

        #: If no item IDs have been passed, check all items
        if self.item_ids:
            for item_id in self.item_ids:
                self.items_to_check.append(self.gis.content.get(item_id))  # pylint: disable=no-member
        else:
            self.items_to_check = self.agol_items

        #: Read the metatable into memory as a dictionary based on itemid.
        #: Getting this once so we don't have to re-read every iteration
        if self.verbose:
            print('Getting metatable info...')

        self.metatable = Metatable()

        sgid_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'Authoritative']
        agol_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'CATEGORY']
        self.metatable.read_metatable(self.sgid_table, sgid_fields)
        self.metatable.read_metatable(self.agol_table, agol_fields)

        if self.metatable.duplicate_keys:
            raise RuntimeError(f'Duplicate AGOL item IDs found in metatables: {self.metatable.duplicate_keys}')

        #: Get the groups
        if self.verbose:
            print('Getting groups...')
        groups = self.gis.groups.search('title:*')  # pylint: disable=no-member
        self.groups_dict = {g.title: g.id for g in groups}

    # except HTTPError:
    #     print(f'Connection error, probably for connection with {credentials.ORG}')
    #     raise

    def check_items(self, report=False):
        """
        Instantiates an ItemChecker for each item and manually runs the
        specified check methods. The results of the checks are saved in
        self.report_dict, which can be used to guide the fixes. Exports the
        final self.report_dict to a csv named checks_yyyy-mm-dd.csv in
        'report_dir', if specified.
        """

        self.log.info(f'Checking {len(self.items_to_check)} items')

        counter = 0
        try:
            for item in self.items_to_check:

                counter += 1

                if self.verbose:
                    print(f'Checking {item.title} ({counter} of {len(self.items_to_check)})...')

                itemid = item.itemid

                #: Initialize empty dictionary for this item
                self.report_dict[itemid] = {}

                checker = checks.ItemChecker(item, self.metatable.metatable_dict)
                retry(lambda: checker.setup(credentials.DB))  # pylint: disable=cell-var-from-loop

                #: TODO: add each method and it's args to a list, then iterate through the list (DRY)

                #: Run the checks on this item
                retry(lambda: checker.tags_check(self.tags_to_delete, self.uppercased_tags, self.articles))  # pylint: disable=cell-var-from-loop
                retry(checker.title_check)
                retry(lambda: checker.folder_check(self.itemid_and_folder))  # pylint: disable=cell-var-from-loop
                retry(checker.groups_check)
                retry(checker.downloads_check)
                retry(checker.delete_protection_check)
                retry(checker.metadata_check)
                retry(lambda: checker.description_note_check(self.static_note, self.shelved_note))  # pylint: disable=cell-var-from-loop
                checker.thumbnail_check(credentials.THUMBNAIL_DIR)
                retry(checker.authoritative_check)
                retry(checker.visibility_check)

                #: Add results to the report
                self.report_dict[itemid].update(checker.results_dict)

        finally:
            if report:
                log_report(self.report_dict, credentials.REPORT_BASE_PATH)

    def fix_items(self, report=False):
        """
        Instantiates an ItemFixer for each item and manually runs the specified
        fix methods using data in self.report_dict. Appends results to
        self.report_dict and writes the whole dictionary to a csv named
        checks_yyyy-mm-dd.csv in 'report_path' (if specified).
        """

        self.log.info(f'Evaluating report for fixes on {len(self.report_dict)} items')

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
                retry(lambda: fixer.metadata_fix(self.metadata_xml_template))  # pylint: disable=cell-var-from-loop
                retry(fixer.tags_fix)
                retry(fixer.title_fix)
                retry(lambda: fixer.group_fix(self.groups_dict))  # pylint: disable=cell-var-from-loop
                retry(fixer.folder_fix)
                retry(fixer.delete_protection_fix)
                retry(fixer.downloads_fix)
                retry(lambda: fixer.description_note_fix(self.static_note, self.shelved_note))  # pylint: disable=cell-var-from-loop
                retry(fixer.thumbnail_fix)
                retry(fixer.authoritative_fix)
                retry(fixer.visibility_fix)

                update_status_keys = [
                    'metadata_result', 'tags_result', 'title_result', 'groups_result', 'folder_result',
                    'delete_protection_result', 'downloads_result', 'description_note_result', 'thumbnail_result',
                    'authoritative_result', 'visibility_result'
                ]

                #: Update summary statistics, print results if verbose
                for status in update_status_keys:

                    #: Skip statuses not updated
                    if 'No update needed for' in item_report[status]:
                        continue

                    #: Increment fixed item summary statistic
                    self.fix_counts.setdefault(status, 0)
                    self.fix_counts[status] += 1
                    #: Log actual fixes
                    if self.verbose:
                        print(f'\t{item_report[status]}')

        except KeyboardInterrupt:
            print('Interrupted by Ctrl-c')
            raise

        finally:
            if report:
                log_report(self.report_dict, credentials.REPORT_BASE_PATH)

            if self.fix_counts:
                for fix_type in self.fix_counts:
                    fix = fix_type.rpartition('_')[0]
                    if fix not in ['thumbnail']:
                        self.log.info(f'{self.fix_counts[fix_type]} items updated for {fix_type}')
            else:
                self.log.info('No items fixed.')

            #: Wipe scratch environment unless verbose (to save metadata xmls for troubleshooting)
            #: TODO: Change so this doesn't stomp other processes using arpcy.env.scratchFolder
            if not self.verbose:
                scratch_path = Path(arcpy.env.scratchFolder)
                for child in scratch_path.iterdir():
                    child.unlink()
