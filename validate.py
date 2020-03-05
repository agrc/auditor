'''
validate.py

Usage:
    validate.py validate --org=<org> --user=<user> [--save_report=<report_path>]

Arguments:
    org           AGOL Portal to connect to [default: https://www.arcgis.com]
    user          AGOL User for authentication
    report_path   Folder to save report to, eg `c:\\temp`

Examples:
    validate.py validate --org=https://www.arcgis.com --user=me --save_report=c:\\temp
'''

import arcgis
import arcpy
import datetime
import getpass
import json

import pandas as pd
from docopt import docopt

import checks, fixes, credentials


class Validator:
    '''
    An object representing an AGOL/Portal organization and information about
    its items. Contains methods for validating and fixing various elements of
    each item's settings (name, tags, group, etc).

    This class contains data and methods specific to all items in the org.
    Specifics to each item should go in the ItemChecker or ItemFixer classes.
    '''

    #: Tags or words that should be uppercased, saved as lower to check against
    uppercased_tags = ['2g', '3g', '4g', 'agol', 'agrc', 'aog', 'at&t', 'blm', 'brat', 'caf', 'cdl', 'daq', 'dfcm', 'dfirm', 'dwq', 'e911', 'ems', 'fae', 'fcc', 'fema', 'gcdb', 'gis', 'gnis', 'hava', 'huc', 'lir', 'lrs', 'lte', 'luca', 'mrrc', 'nca', 'ng911', 'nox', 'npsbn', 'ntia', 'nwi', 'plss', 'pm10', 'psap', 'sbdc', 'sbi', 'sgid', 'sitla', 'sligp', 'trax', 'uca', 'udot', 'ugs', 'uhp', 'uic', 'us', 'usdw', 'usfs', 'usfws', 'usps', 'ustc', 'ut', 'uta', 'vcp', 'vista', 'voc']

    #: Articles that should be left lowercase.
    articles = ['a', 'the', 'of', 'is', 'in']

    #: Tags that should be deleted
    tags_to_delete = ['.sd', 'service definition']

    #: Notes for static and shelved descriptions
    static_note = "<i><b>NOTE</b>: This dataset holds 'static' data that we don't expect to change. We have removed it from the SDE database and placed it in ArcGIS Online, but it is still considered part of the SGID and shared on opendata.gis.utah.gov.</i>"

    shelved_note = "<i><b>NOTE</b>: This dataset is an older dataset that we have removed from the SGID and 'shelved' in ArcGIS Online. There may (or may not) be a newer vintage of this dataset in the SGID.</i>"

    def __init__(self, portal, user, metatable, agol_table, verbose=False):
        '''
        Create an arcgis.gis.GIS object for 'user' at 'portal'. Automatically
        create a list of all the Feature Service objects in the user's folders
        and a dictionary of each item's folder based on itemid. Read 'metatable'
        and agol_table into a dictionary based on the itemid.
        '''
        
        #: A list of log entries, format TBD
        self.report_dict = {}

        #: A list of feature service item objects generated by trawling all of 
        #: the user's folders
        self.feature_service_items = []

        #: A dictionary of items and their folder
        self.itemid_and_folder = {}

        #: A dictionary of the metatable records, indexed by the metatable's itemid
        #: values: {item_id: [table_sgid_name, table_agol_name, table_category]}
        self.metatable_dict = {}

        #: A dictionary of groups and their ID:
        self.groups_dict = {}

        self.verbose = verbose

        self.username = user
        self.gis = arcgis.gis.GIS(portal, user, getpass.getpass(f'{user}\'s password for {portal}:'))

        user_item = self.gis.users.me

        #: Build list of folders. 'None' gives us the root folder.
        if self.verbose:
            print(f'Getting {user}\'s folders...')
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

        meta_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME']
        meta_dupes = self.read_metatable(metatable, meta_fields)

        agol_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'CATEGORY']
        agol_dupes = self.read_metatable(agol_table, agol_fields)

        if meta_dupes:
            duplicate_keys.append(meta_dupes)
        if agol_dupes:
            duplicate_keys.append(agol_dupes)

        if duplicate_keys:
            raise RuntimeError(f'Duplicate AGOL item IDs found in metatables: {duplicate_keys}')

        #: Get the groups
        if self.verbose:
            print('Getting groups...')
        groups = self.gis.groups.search('title:*')
        self.groups_dict = {g.title: g.id for g in groups}


    def read_metatable(self, table, fields):
        '''
        Read metatable 'table' into self.metatable_dict.

        Returns: list of any duplicate AGOL item ids found 
        '''

        duplicate_keys = []

        with arcpy.da.SearchCursor(table, fields) as meta_cursor:
            for row in meta_cursor:

                if len(fields) == 3:  #: AGOLItems table only has three fields
                    table_sgid_name, table_agol_itemid, table_agol_name = row
                    table_category = 'SGID'

                else:  #: Shelved table hosted in AGOL has four fields
                    table_sgid_name, table_agol_itemid, table_agol_name, table_category = row

                if table_agol_itemid:  #: Don't evaluate null itemids
                    if table_agol_itemid not in self.metatable_dict:
                        self.metatable_dict[table_agol_itemid] = [table_sgid_name, table_agol_name, table_category]
                    else:
                        duplicate_keys.append(table_agol_itemid)

        return duplicate_keys


    def check_items(self, report_path=None):
        '''
        For each hosted feature layer, check:
            > Tags for malformed spacing, standard AGRC/SGID tags
                item.update({'tags':[tags]})
            > Group & Folder (?) to match source data category
                gis.content.share(item, everyone=True, groups=<Open Data Group>)
                item.move(folder)
            > Delete Protection enabled
                item.protect=True
            > Downloads enabled
                manager = arcgis.features.FeatureLayerCollection.fromitem(item).manager
                manager.update_definition({ 'capabilities': 'Query,Extract' })
            > Title against metatable
                item.update({'title':title})
            > Metadata against SGID (Waiting until 2.5's arcpy metadata tools?)
        '''

        for item in self.feature_service_items:
            
            if self.verbose:
                print(f'Checking {item.title}...')
            
            itemid = item.itemid

            #: Initialize empty dictionary for this item
            self.report_dict[itemid] = {}

            checker = checks.ItemChecker(item, self.metatable_dict, credentials.DB)

            #: Run the checks on this item
            checker.tags_check(self.tags_to_delete, self.uppercased_tags, self.articles)
            checker.title_check()
            checker.folder_check(self.itemid_and_folder)
            checker.groups_check()
            checker.downloads_check()
            checker.delete_protection_check()
            checker.metadata_check()
            checker.description_note_check(self.static_note, self.shelved_note)
            checker.thumbnail_check(credentials.THUMBNAIL_DIR)

            #: Add results to the report
            self.report_dict[itemid].update(checker.results_dict)

        #: Convert dict to pandas df for easy writing
        if report_path:
            report_df = pd.DataFrame(self.report_dict).T
            report_df.to_csv(report_path)


    def fix_items(self, report_path=None):
        '''
        Perform any needed fixes by looping through report dictionary and
        checking the various _fix entries. Append results string to report
        dictionary and write to report_path (if specified).
        '''

        try:
            for itemid in self.report_dict:

                item = self.gis.content.get(itemid)
                item_report = self.report_dict[itemid]
                
                if self.verbose:
                    print(f'Evaluating report for fixes on {item.title}...')
                
                fixer = fixes.ItemFixer(item, item_report)

                fixer.metadata_fix(self.static_note, self.shelved_note)
                fixer.tags_or_title_fix()
                fixer.group_fix(self.groups_dict)
                fixer.folder_fix()
                fixer.delete_protection_fix()
                fixer.downloads_fix()
                fixer.description_note_fix(self.static_note, self.shelved_note)
                fixer.thumbnail_fix()

                update_status_keys = ['metadata_result', 'tags_title_result', 'groups_result', 'folder_result', 'delete_protection_result', 'downloads_result', 'description_note_result', 'thumbnail_result']

                if self.verbose:
                    for status in update_status_keys:
                        if 'No update needed for' not in item_report[status]:
                            print(f'\t{item_report[status]}')


        finally:
            #: Convert dict to pandas df for easy writing
            if report_path:
                report_df = pd.DataFrame(self.report_dict).T
                report_df.to_csv(report_path)


if __name__ == '__main__':
    metatable = r'C:\gis\Projects\Data\internal.agrc.utah.gov.sde\SGID.META.AGOLItems'
    agol_table = r'https://services1.arcgis.com/99lidPhWCzftIe9K/arcgis/rest/services/metatable_test/FeatureServer/0'

    agrc = Validator('https://www.arcgis.com', 'UtahAGRC', metatable, agol_table, verbose=True)
    agrc.check_items(r'c:\temp\validator11_thumbnails.csv')

    # test_metatable = r'C:\gis\Projects\Data\data.gdb\validate_test_table'

    # jake = Validator('https://www.arcgis.com', 'Jake.Adams@UtahAGRC', metatable, agol_table, verbose=True)
    # jake.check_items(r'c:\temp\validator11_jake.csv')
    # jake.fix_items(r'c:\temp\validator11_jake_fixes.csv')