"""
checks.py: contains ItemChecker class for evaluating an item's metadata, etc and determining needed fixes.
"""
import json

from pathlib import Path
from collections import namedtuple

import arcgis
import arcpy


def tag_case(tag, uppercased, articles):
    """
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
    """

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
    """
    Return the appropriate group title based on either the SGID table name or
    the shelved category.
    """

    sgid_name, _, item_category, _ = metatable_dict_entry

    if item_category == 'shelved':
        group = 'AGRC Shelf'
    else:
        table_category = sgid_name.split('.')[1].title()
        group = f'Utah SGID {table_category}'

    return group


def get_item_properties(item):
    """
    Gets all the relevant info about item in successive calls; seems to speed up times by about .5 to 1 second per item.
    """
    ItemProperties = namedtuple(
        'ItemProperties',
        ['title', 'tags', 'shared_with', 'itemid', 'protected', 'description', 'metadata', 'content_status', 'layers']
    )

    title = item.title
    tags = item.tags
    try:
        shared_with = item.shared_with
    except Exception as ex:
        shared_with = ex
    itemid = item.itemid
    protected = item.protected
    description = item.description
    metadata = item.metadata
    content_status = item.content_status
    layers = item.layers

    item_properties = ItemProperties(
        title, tags, shared_with, itemid, protected, description, metadata, content_status, layers
    )

    return item_properties


class ItemChecker:
    """
    Class to check an AGOL item. Uses a metatable entry for most information;
    the tag check is the only check that doesn't rely on the metatables.
    __init__() gets what the values should be from the metatable and stores them
    as instance variables. The x_check() methods then use the instance variable
    to check against the item's existing data.

    This class is specific to a single item. General org-level data (like lists
    of tags to uppercase, etc) should be stored in the Auditor class and
    passed to methods if needed.

    The results_dict dictionary holds the results of every check that is
    completed. If a check isn't performed, it's results aren't added to the
    dictionary via results_dict.update().
    """

    def __init__(self, item, metatable_dict):

        #: Set up our results dict with first column after AGOL ID being SGID
        #: name, if applicable
        self.results_dict = {}
        self.results_dict['SGID_Name'] = ''

        self.item = get_item_properties(item)
        self.metatable_dict = metatable_dict

        #: Get the REST properties object once
        try:
            manager = arcgis.features.FeatureLayerCollection.fromitem(self.item).manager
            self.properties = json.loads(str(manager.properties))
        except:  # pylint: disable=bare-except
            self.properties = None

        #: These may or may not be used outside their specific check methods
        self.new_tags = []
        self.downloads = False
        self.protect = False
        self.static_shelved = None
        self.set_visibility = False

        #: These maybe overwritten below if the item is in the SGID
        self.in_sgid = False
        self.title_from_metatable = None
        self.new_group = None
        self.arcpy_metadata = None
        self.feature_class_path = None
        self.new_folder = None
        self.authoritative = ''

    def setup(self, sde_path):
        """
        Sets up the checker's properties with data from the metatable, feature
        class, and AGOL item.

        sde_path:   Path to the SDE database. Joined with the feature class
                    name obtained from the metatable.
        """
        #: Get title, group from metatable if it's in the table
        if self.item.itemid in self.metatable_dict:
            self.in_sgid = True
            self.title_from_metatable = self.metatable_dict[self.item.itemid][1]
            self.new_group = get_group_from_table(self.metatable_dict[self.item.itemid])
            if self.metatable_dict[self.item.itemid][3]:
                if self.metatable_dict[self.item.itemid][3].casefold() == 'y':
                    self.authoritative = 'public_authoritative'
                elif self.metatable_dict[self.item.itemid][3].casefold() == 'd':
                    self.authoritative = 'deprecated'

            feature_class_name = self.metatable_dict[self.item.itemid][0]
            self.results_dict['SGID_Name'] = feature_class_name
            self.feature_class_path = Path(sde_path, feature_class_name)
            if arcpy.Exists(str(self.feature_class_path)):
                self.arcpy_metadata = arcpy.metadata.Metadata(str(self.feature_class_path))

        #: Get folder from SGID category if it's in the table
        if self.new_group == 'AGRC Shelf':
            self.new_folder = 'AGRC_Shelved'
        elif self.new_group:
            self.new_folder = self.new_group.split('Utah SGID ')[-1]

        #: Set static/shelved flag
        if self.new_group == 'AGRC Shelf':
            self.static_shelved = 'shelved'
        elif self.in_sgid and self.metatable_dict[self.item.itemid][2] == 'static':
            self.static_shelved = 'static'

    def tags_check(self, tags_to_delete, uppercased_tags, articles):
        """
        Create a list of new, cleaned tags:
            * Properly case tags using uppercased_tags and articles
            * Delete any tags in tags_to_delete
            * Add SGID category tag and SGID, AGRC if it's an SGID item

        Update results_dict with results for this item:
                {'tags_fix':'', 'tags_old':'', 'tags_new':''}
        """

        #: Use existing title unless we have one from metatable
        if self.title_from_metatable:
            title = self.title_from_metatable
        else:
            title = self.item.title

        #: Strip off any leading/trailing whitespace
        orig_tags = [t.strip() for t in self.item.tags if t.strip()]

        #: Add any tags in the metadata to list of tags to evaluate
        if self.arcpy_metadata and self.arcpy_metadata.tags:
            orig_tags.extend([t.strip() for t in self.arcpy_metadata.tags.split(', ') if t.strip()])

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
            #: Safe to use lower case for single-word tags
            single_word_tag_in_title = False
            if orig_tag.lower() in title.lower().split():
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
                cased_tag = tag_case(orig_tag, uppercased_tags, articles)
                if cased_tag not in self.new_tags:
                    self.new_tags.append(cased_tag)

        #: Check the category tag. If it doesn't exist, set to None
        group_tag = None
        if self.static_shelved == 'shelved':
            group_tag = 'Shelved'
        elif self.new_group:
            group_tag = self.new_group.split('Utah SGID ')[-1]

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
        #: Report existing tags for troubleshooting why some items don't seem to be checked during weekly run.
        tags_data = {'tags_fix': 'N', 'tags_old': self.item.tags, 'tags_new': ''}

        if sorted(self.new_tags) != sorted(self.item.tags):
            tags_data = {'tags_fix': 'Y', 'tags_old': self.item.tags, 'tags_new': self.new_tags}

        self.results_dict.update(tags_data)

    def title_check(self):
        """
        Check item's title against title in metatable.

        Update results_dict with results for this item:
                {'title_fix':'', 'title_old':'', 'title_new':''}
        """

        #: Create title data: title_fix, title_old, title_new
        #: Always include the old title for readability
        title_data = {'title_fix': 'N', 'title_old': self.item.title, 'title_new': ''}

        #: Will be updated from metatable and/or deprecated check.
        new_title = self.item.title

        #: Existing title with {Deprecated} removed if necessary
        existing_title = self.item.title
        if self.item.title.startswith('{Deprecated} '):
            existing_title = self.item.title.split(' ', 1)[-1]

        #: Check to see if title needs updating from metatable, taking into account the metatable title
        #: won't have {Deprecated} at the front
        if self.title_from_metatable and self.title_from_metatable != existing_title:
            new_title = self.title_from_metatable
            title_data = {'title_fix': 'Y', 'title_old': self.item.title, 'title_new': new_title}

        #: Add {Deprecated} if necessary
        #: new_title will have been modified from previous step if necessary
        if self.authoritative == 'deprecated' and 'deprecated' not in new_title.casefold():
            new_title = '{Deprecated} ' + new_title
            title_data = {'title_fix': 'Y', 'title_old': self.item.title, 'title_new': new_title}

        self.results_dict.update(title_data)

    def folder_check(self, itemid_and_folder):
        """
        Check item's folder against SGID category name from metatable.

        Update results_dict with results for this item:
                {'folder_fix':'', 'folder_old':'', 'folder_new':''}
        """

        #: Get current folder from dictionary of items' folders
        current_folder = itemid_and_folder[self.item.itemid]

        #: Create folder data: folder_fix, folder_old, folder_new
        folder_data = {'folder_fix': 'N', 'folder_old': '', 'folder_new': ''}

        if self.new_folder and self.new_folder != current_folder:
            folder_data = {'folder_fix': 'Y', 'folder_old': current_folder, 'folder_new': self.new_folder}

        self.results_dict.update(folder_data)

    def groups_check(self):
        """
        Check item's group against SGID category from metatable.

        Update results_dict with results for this item:
                {'groups_fix':'', 'groups_old':'', 'group_new':''}
        """

        #: Get current group, wrapped in try/except for groups that error out
        try:
            current_groups = [group.title for group in self.item.shared_with['groups']]
        except:  # pylint: disable=bare-except
            current_groups = ['Error']

        #: Create groups data: groups_fix, groups_old, group_new
        groups_data = {'groups_fix': 'N', 'groups_old': '', 'group_new': ''}

        if current_groups and current_groups[0].casefold() == 'error':
            groups_data = {'groups_fix': 'N', 'groups_old': 'Can\'t get group', 'group_new': ''}
        elif self.new_group and self.new_group not in current_groups:
            groups_data = {'groups_fix': 'Y', 'groups_old': current_groups, 'group_new': self.new_group}

        self.results_dict.update(groups_data)

    def downloads_check(self):
        """
        Make sure item's 'Allow others to export to different formats' box is checked

        Update results_dict with results for this item:
                {'downloads_fix':''}
        """

        #: Check if downloads enabled; wrap in try/except for robustness
        try:
            manager = arcgis.features.FeatureLayerCollection.fromitem(self.item).manager
            properties = json.loads(str(manager.properties))
        except:  # pylint: disable=bare-except
            properties = None

        #: Create protect data: downloads_fix
        fix_downloads = {'downloads_fix': 'N'}

        if self.in_sgid and properties and 'Extract' not in properties['capabilities']:
            self.downloads = True
            fix_downloads = {'downloads_fix': 'Y'}

        self.results_dict.update(fix_downloads)

    def delete_protection_check(self):
        """
        Prevent item from being accidentally deleted.

        Update results_dict with results for this item:
                {'delete_protection_fix':''}
        """

        protect_data = {'delete_protection_fix': 'N'}

        #: item.protected is Boolean
        if self.in_sgid and not self.item.protected:
            self.protect = True
            protect_data = {'delete_protection_fix': 'Y'}

        self.results_dict.update(protect_data)

    def metadata_check(self):
        """
        Check item's .metadata property against the .xml property of it's source
        feature class.

        Update results_dict with results:
                {'metadata_fix': '', 'metadata_old': '', 'metadata_new': '',
                 'metadata_note': ''}
            Where metadata_old is the string from item.metdata, metadata_new
            is path to feature class, and metadata_note is either '',
            'shelved', or 'static'
        """

        metadata_data = {
            'metadata_fix': 'N',
            'metadata_old': '',
            'metadata_new': '',
            'metadata_note': '',
        }

        if self.arcpy_metadata and self.arcpy_metadata.xml != self.item.metadata:
            metadata_data = {
                'metadata_fix': 'Y',
                'metadata_old': 'item.metadata from AGOL not shown due to length',
                'metadata_new': str(self.feature_class_path),
                'metadata_note': ''
            }

            # Update flag for description note for shelved/static data
            if self.new_group == 'AGRC Shelf':
                metadata_data['metadata_note'] = 'shelved'
            elif self.metatable_dict[self.item.itemid][2] == 'static':
                metadata_data['metadata_note'] = 'static'

        self.results_dict.update(metadata_data)

    def description_note_check(self, static_note, shelved_note):
        """
        Check to see if the AGOL description begins with static_note or
        shelved_note.

        Update results_dict with results:
                {'description_note_fix': '',
                 'description_note_source': 'static' or 'shelved'}
        """

        description_data = {'description_note_fix': 'N', 'description_note_source': ''}

        if self.static_shelved == 'static' and not self.item.description.startswith(static_note):
            description_data = {'description_note_fix': 'Y', 'description_note_source': 'static'}
        elif self.static_shelved == 'shelved' and not self.item.description.startswith(shelved_note):
            description_data = {'description_note_fix': 'Y', 'description_note_source': 'shelved'}

        self.results_dict.update(description_data)

    def thumbnail_check(self, thumbnail_dir):
        """
        Create the path to the appropriate thumbnail if the item is in an SGID
        group or is shelved.

        Update results_dict with results:
                {'thumbnail_fix': '', 'thumbnail_path': ''}
        """

        thumbnail_data = {'thumbnail_fix': 'N', 'thumbnail_path': ''}

        if self.new_group:
            group = self.new_group.split()[-1].casefold()

            thumbnail_path = Path(thumbnail_dir, f'{group}.png')
            thumbnail_data = {'thumbnail_fix': 'Y', 'thumbnail_path': str(thumbnail_path)}

            if not thumbnail_path.exists():
                thumbnail_data = {'thumbnail_fix': 'N', 'thumbnail_path': f'Thumbnail not found: {thumbnail_path}'}

        self.results_dict.update(thumbnail_data)

    def authoritative_check(self):
        """
        Check if the item is set to authoritative or deprecated via the
        item.content_status property.

        Update results_dict with results:
                {'authoritative_fix': 'N', 'authoritative_old': '',
                 'authoritative_new': ''}
        """

        authoritative_data = {'authoritative_fix': 'N', 'authoritative_old': '', 'authoritative_new': ''}

        #: item.content_status can be 'public_authoritative', 'deprecated', or ''
        if self.in_sgid and self.item.content_status != self.authoritative:
            authoritative_data = {
                'authoritative_fix': 'Y',
                'authoritative_old': f'{self.item.content_status}',
                'authoritative_new': self.authoritative
            }
            #: item.content_status returns an empty string if it's not
            #: authoritative/deprecated.
            if not self.item.content_status:
                authoritative_data['authoritative_old'] = '\' \''

        self.results_dict.update(authoritative_data)

    def visibility_check(self):
        """
        Make sure item's default visibility is set to True

        Update results_dict with results for this item:
                {'visibility_fix':''}
        """

        fix_visibility = {'visibility_fix': 'N'}

        for layer in self.item.layers:

            #: Check if default vis is true; wrap in try/except for robustness
            properties = None
            try:
                properties = json.loads(str(layer.manager.properties))
            except:  # pylint: disable=bare-except
                pass

            if properties and not properties['defaultVisibility']:
                self.set_visibility = True

        if self.set_visibility:
            fix_visibility['visibility_fix'] = 'Y'

        self.results_dict.update(fix_visibility)

    def cache_age_check(self, max_age):
        """
        Make sure the cacheMaxAge setting matches the desired time. Sets the "Cache Control" value in the AGOL
        item settings.

        Update results_dict with results for this item:
                {'cache_age_fix':'', 'cache_age_old':'', 'cache_age_new:''}
        """

        #: Create protect data: downloads_fix
        fix_cache_age = {'cache_age_fix': 'N', 'cache_age_old': '', 'cache_age_new': ''}

        if self.in_sgid and self.properties:
            current_age = self.properties['adminServiceInfo']['cacheMaxAge']
            if current_age != max_age:
                fix_cache_age = {'cache_age_fix': 'Y', 'cache_age_old': current_age, 'cache_age_new': max_age}

        self.results_dict.update(fix_cache_age)
