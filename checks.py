import arcgis
import arcpy
import json

from os.path import join

import credentials

def tag_case(tag, uppercased, articles):
    '''
    Changes a tag to the correct title case while also removing any periods:
    'U.S. bureau Of Geoinformation' -> 'US Bureau of Geoinformation'. Should
    properly upper-case any words or single tags that are acronyms:
    'agrc' -> 'AGRC', 'Plss Fabric' -> 'PLSS Fabric'. Any words separated by
    a hyphen will also be title-cased: 'water-related' -> 'Water-Related'.

    Note: No check is done for articles at the begining of a tag; all articles
    will be lowercased.

    tag:        The single or multi-word tag to check
    uppercased: Lower-cased list of words that should be uppercased (must be 
                lower-cased to facilitate checking)
    articles:   Lower-cased list of words that should always be lower-cased:
                'in', 'of', etc
    '''

    new_words = []
    for word in tag.split():
        cleaned_word = word.replace('.', '')
        
        #: Upper case specified words:
        if cleaned_word.lower() in uppercased:
            new_words.append(cleaned_word.upper())
        #: Lower case articles/conjunctions 
        elif cleaned_word.lower() in articles:
            new_words.append(cleaned_word.lower())
        #: Title case everything else
        else:
            new_words.append(cleaned_word.title())

    return ' '.join(new_words)


def get_group_from_table(metatable_dict_entry):
    '''
    Return the appropriate group title based on either the SGID table name or
    the shelved category.
    '''

    SGID_name, _, item_category = metatable_dict_entry

    if item_category == 'shelved':
        group = 'AGRC Shelf'
    else:
        table_category = SGID_name.split('.')[1].title()
        group = f'Utah SGID {table_category}'     

    return group


class ItemChecker:
    '''
    Class to validate an AGOL item. Uses a metatable entry if possible for some
    information. Tags (partially), download options, and delete protection
    don't rely on the metatable. __init__() gets what the values should be from
    the metatable and stores them as instance variables. The x_check() methods
    then use the instance variable to check against the item's existing data.

    This class is specific to a single item. General org-level data should be
    stored in the Validate class and passed to methods if needed (like lists of 
    tags to uppercase, etc).

    The results_dict dictionary holds the results of every check that is
    completed. If a check isn't performed, it's results aren't added to the
    dictionary via results_dict.update().
    '''

    def __init__(self, item, metatable_dict):


        self.results_dict = {}

        self.item = item
        self.metatable_dict = metatable_dict
        
        self.new_tags = []
        self.downloads = False
        self.protect = False
        self.static_shelved = None


        #: Get title, group from metatable if it's in the table
        if self.item.itemid in self.metatable_dict:
            self.new_title = self.metatable_dict[self.item.itemid][1]
            self.new_group = get_group_from_table(self.metatable_dict[self.item.itemid])
            
            feature_class_name = self.metatable_dict[self.item.itemid][0]
            self.feature_class_path = join(credentials.DB, feature_class_name)
            if arcpy.Exists(self.feature_class_path):
                self.arcpy_metadata = arcpy.metadata.Metadata(self.feature_class_path)
            else:
                self.arcpy_metadata = None
        else:
            self.new_title = None
            self.new_group = None
            self.arcpy_metadata = None
            self.feature_class_path = None

        #: Get folder from SGID category if it's in the table
        if self.new_group == 'AGRC Shelf':
            self.new_folder = 'AGRC_Shelved'
        elif self.new_group:
            self.new_folder = self.new_group.split('Utah SGID ')[-1]
        else:
            self.new_folder = None

        #: Set static/shelved flag
        if self.new_group == 'AGRC Shelf':
            self.static_shelved = 'shelved'
        elif self.item.itemid in self.metatable_dict and self.metatable_dict[self.item.itemid][2] == 'static':
            self.static_shelved = 'static'



    def tags_check(self, tags_to_delete, uppercased_tags, articles):
        '''
        Create a list of new, cleaned tags:
            * Properly case tags using uppercased_tags and articles
            * Delete any tags in tags_to_delete
            * Add SGID category tag and SGID, AGRC if it's an SGID item

        Update results_dict with results for this item:
                {'tags_fix':'', 'tags_old':'', 'tags_new':''}
        '''

        #: Use existing title unless we have one from metatable
        if self.new_title:
            title = self.new_title
        else:
            title = self.item.title

        #: Strip off any leading/trailing whitespace
        orig_tags = [t.strip() for t in self.item.tags]

        #: Add any tags in the metadata to list of tags to evaluate
        if self.arcpy_metadata and self.arcpy_metadata.tags:
            orig_tags.extend([t.strip() for t in self.arcpy_metadata.tags.split(', ')])

        #: Evaluate existing tags
        for orig_tag in orig_tags:

            #: Check if the tag is in the title (checking orig_tag instead
            #: of cleaned_tag to avoid weird false positives in multi-word
            #: tags catching the middle of a title- ie, 'Cycle Net' would
            #: match the title 'Bicycle Network'. Probably not super
            #: common, but oh well.)
            #: These combine several boolean checks into a single variable
            #: to be checked later.

            #: single-word tag in title
            single_word_tag_in_title = False
            if orig_tag in title.split():
                single_word_tag_in_title = True
            #: multi-word tag in title
            multi_word_tag_in_title = False
            if ' ' in orig_tag and orig_tag in title:
                multi_word_tag_in_title = True

            #: operate on lower case to fix any weird mis-cased tags
            lowercase_tag = orig_tag.lower()

            #: Run checks on existing tags. A check that modifies the tag should
            #: append it to new_tags. A check that removes unwanted tags
            #: should just pass. If a tag passes all the checks, it gets
            #: properly cased and added to new_tags (the else clause).

            #: Fix/keep 'Utah' if it's not in the title
            if lowercase_tag == 'utah':
                #: Have to nest this to avoid 'utah' hitting else and being added
                if 'Utah' not in title.split():
                    self.new_tags.append('Utah')
            #: Don't add to new_tags if it should be deleted
            elif lowercase_tag in tags_to_delete:
                pass
            #: Don't add if it's in the title
            elif single_word_tag_in_title or multi_word_tag_in_title:
                pass
            #: Otherwise, add the tag (properly-cased)
            else:
                cased_tag = tag_case(orig_tag, uppercased_tags,  articles)
                if cased_tag not in self.new_tags:
                    self.new_tags.append(cased_tag)
        
        #: Check the category tag
        if self.static_shelved == 'shelved':
            group_tag = 'Shelved'
        elif self.new_group:  #: If it exists, extract the group
            group_tag = self.new_group.split('Utah SGID ')[-1]
        else:  #: If it doesn't exist, set to None
            group_tag = None

        if group_tag:
            #: If there's already a lowercase tag for the category, replace it
            if group_tag.lower() in self.new_tags:
                self.new_tags.remove(group_tag.lower())
                self.new_tags.append(group_tag)
            #: Otherwise add if its not in list already
            elif group_tag not in self.new_tags:
                self.new_tags.append(group_tag)

            #: Static items should be tagged 'Static'
            if self.static_shelved == 'static':
                if 'Static' not in self.new_tags:
                    self.new_tags.append('Static')
                if 'Shelved' in self.new_tags:
                    self.new_tags.remove('Shelved')

            #: Make sure it's got SGID, AGRC in it's tags
            if 'SGID' not in self.new_tags:
                self.new_tags.append('SGID')
            if 'AGRC' not in self.new_tags:
                self.new_tags.append('AGRC')

        #: Create tags data: tags_fix, tags_old, tags_new
        if sorted(self.new_tags) != sorted(self.item.tags):
            tags_data = {'tags_fix':'Y', 'tags_old':self.item.tags, 'tags_new':self.new_tags}
        else:
            tags_data = {'tags_fix':'N', 'tags_old':'', 'tags_new':''}

        self.results_dict.update(tags_data)


    def title_check(self):
        '''
        Check item's title against title in metatable.

        Update results_dict with results for this item:
                {'title_fix':'', 'title_old':'', 'title_new':''}
        '''

        #: Create title data: title_fix, title_old, title_new
        #: Always include the old title for readability
        if self.new_title and self.new_title != self.item.title:
            title_data = {'title_fix':'Y', 'title_old':self.item.title, 'title_new':self.new_title}
        else:
            title_data = {'title_fix':'N', 'title_old':self.item.title, 'title_new':''}  

        self.results_dict.update(title_data)


    def folder_check(self, itemid_and_folder):
        '''
        Check item's folder against SGID category name from metatable.

        Update results_dict with results for this item:
                {'folder_fix':'', 'folder_old':'', 'folder_new':''}
        '''

        #: Get current folder from dictionary of items' folders
        current_folder = itemid_and_folder[self.item.itemid]

        #: Create folder data: folder_fix, folder_old, folder_new
        if self.new_folder and self.new_folder != current_folder:
            folder_data = {'folder_fix':'Y', 'folder_old':current_folder, 'folder_new':self.new_folder}
        else:
            folder_data = {'folder_fix':'N', 'folder_old':'', 'folder_new':''} 

        self.results_dict.update(folder_data)


    def groups_check(self):
        '''
        Check item's group against SGID category from metatable.

        Update results_dict with results for this item:
                {'groups_fix':'', 'groups_old':'', 'group_new':''}
        '''

        #: Get current group, wrapped in try/except for groups that error out
        try:
            current_groups = [group.title for group in self.item.shared_with['groups']]
        except:
            current_groups = ['Error']

        #: Create groups data: groups_fix, groups_old, group_new
        if current_groups == 'Error':
            groups_data = ['N', 'Can\'t get group', '']
        elif self.new_group and self.new_group not in current_groups:
            groups_data = {'groups_fix':'Y', 'groups_old':current_groups, 'group_new':self.new_group}
        else:
            groups_data = {'groups_fix':'N', 'groups_old':'', 'group_new':''}

        self.results_dict.update(groups_data)


    def downloads_check(self):
        '''
        Make sure item's 'Allow others to export to different formats' box is checked

        Update results_dict with results for this item:
                {'downloads_fix':''}
        '''

        #: Check if downloads enabled; wrap in try/except for robustness
        try:
            manager = arcgis.features.FeatureLayerCollection.fromitem(self.item).manager
            properties = json.loads(str(manager.properties))
        except:
            properties = None
        
        #: Create protect data: downloads_fix
        if properties and 'Extract' not in properties['capabilities']:
            self.downloads = True
            fix_downloads = {'downloads_fix':'Y'}
        else:
            fix_downloads = {'downloads_fix':'N'}

        self.results_dict.update(fix_downloads)


    def delete_protection_check(self):
        '''
        Prevent item from being accidentally deleted.

        Update results_dict with results for this item:
                {'delete_protection_fix':''}
        '''

        #: item.protected is Boolean
        if not self.item.protected:
            self.protect = True
            protect_data = {'delete_protection_fix':'Y'}
        else:
            protect_data = {'delete_protection_fix':'N'}

        self.results_dict.update(protect_data)


    def metadata_check(self):


        if self.arcpy_metadata and self.arcpy_metadata.xml != self.item.metadata:
            metadata_data = {'metadata_fix': 'Y', 'metadata_old': self.item.metadata, 'metadata_new': self.feature_class_path}

            # Set flag for description note for shelved/static data
            if self.new_group == 'AGRC Shelf':
                metadata_data['metadata_note'] = 'shelved'
            elif self.metatable_dict[self.item.itemid][2] == 'static':
                metadata_data['metadata_note'] = 'static'
            else:
                metadata_data['metadata_note'] = ''

        else:
            metadata_data = {'metadata_fix': 'N', 'metadata_old': '', 'metadata_new': '', 'metadata_note': ''}

        self.results_dict.update(metadata_data)

    def description_note_check(self, static_note, shelved_note):

        if self.static_shelved == 'static' and not self.item.description.startswith(static_note):
            description_data = {'description_note_fix': 'Y', 'description_note_source': 'static'}
        elif self.static_shelved == 'shelved' and not self.item.description.startswith(shelved_note):
            description_data = {'description_note_fix': 'Y', 'description_note_source': 'shelved'}
        else:
            description_data = {'description_note_fix': 'N', 'description_note_source': ''}

        self.results_dict.update(description_data)