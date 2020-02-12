import arcgis
import json

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


def tags_check(item, tags_to_delete, uppercased_tags, articles, metatable_dict):
    '''
    Create a list of new, cleaned tags:
        * Properly case tags using uppercased_tags and articles
        * Delete any tags in tags_to_delete
        * Add SGID category tag and SGID, AGRC if it's an SGID item

    return: Dict of update info:
            {'tags_fix':'', 'tags_old':'', 'tags_new':''}
    '''

    #: Use existing title unless we have one from metatable
    title = item.title
    if item.itemid in metatable_dict:
        item_title = metatable_dict[item.itemid][1]
        if item_title:
            title = item_title
    
    #: Strip off any leading/trailing whitespace
    orig_tags = [t.strip() for t in item.tags]

    #: Good tags that can be used to overwrite all existing tags
    new_tags = []

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
                new_tags.append('Utah')
        #: Don't add to new_tags if it should be deleted
        elif lowercase_tag in tags_to_delete:
            pass
        #: Don't add if it's in the title
        elif single_word_tag_in_title or multi_word_tag_in_title:
            pass
        #: Otherwise, add the tag (properly-cased)
        else:
            cased_tag = tag_case(orig_tag, uppercased_tags,  articles)
            if cased_tag not in new_tags:
                new_tags.append(cased_tag)
    
    #: Check the category tag
    if item.itemid in metatable_dict:
        group = get_group_from_table(metatable_dict[item.itemid])
        if group == 'AGRC Shelf':
            group_tag = 'Shelved'
        else:
            group_tag = group.split('Utah SGID ')[-1]

        #: If there's already a lowercase tag for the category, replace it
        if group_tag.lower() in new_tags:
            new_tags.remove(group_tag.lower())
            new_tags.append(group_tag)
        #: Otherwise add if its not in list already
        elif group_tag not in new_tags:
            new_tags.append(group_tag)

        #: Static items should be tagged 'Static'
        if metatable_dict[item.itemid][2] == 'static':
            if 'Static' not in new_tags:
                new_tags.append('Static')
            if 'Shelved' in new_tags:
                new_tags.remove('Shelved')

        #: Make sure it's got SGID, AGRC in it's tags
        if 'SGID' not in new_tags:
            new_tags.append('SGID')
        if 'AGRC' not in new_tags:
            new_tags.append('AGRC')

    #: Create tags data: tags_fix, tags_old, tags_new
    if sorted(new_tags) != sorted(item.tags):
        tags_data = {'tags_fix':'Y', 'tags_old':item.tags, 'tags_new':new_tags}
    else:
        tags_data = {'tags_fix':'N', 'tags_old':'', 'tags_new':''}

    return tags_data


def title_check(item, metatable_dict):
    '''
    Check item's title against title in metatable.

    return: Dict of update info:
            {'title_fix':'', 'title_old':'', 'title_new':''}
    '''

    #: Get title from metatable if it's in the table
    if item.itemid in metatable_dict:
        table_agol_title = metatable_dict[item.itemid][1]
    else:
        table_agol_title = None

    #: Create title data: title_fix, title_old, title_new
    #: Always include the old title for readability
    if table_agol_title and table_agol_title != item.title:
        title_data = {'title_fix':'Y', 'title_old':item.title, 'title_new':table_agol_title}
    else:
        title_data = {'title_fix':'N', 'title_old':item.title, 'title_new':''}  

    return title_data


def folder_check(item, metatable_dict, itemid_and_folder):
    '''
    Check item's folder against SGID category name from metatable.

    return: Dict of update info:
            {'folder_fix':'', 'folder_old':'', 'folder_new':''}
    '''

    #: Get current folder from dictionary of items' folders
    current_folder = itemid_and_folder[item.itemid]

    #: Get folder from SGID category if in metatable
    if item.itemid in metatable_dict:
        SGID_name, _, category = metatable_dict[item.itemid]
        if category == 'shelved':
            table_folder = 'AGRC_Shelved'
        else:
            table_folder = SGID_name.split('.')[1].title()
    else:
        table_folder = None

    #: Create folder data: folder_fix, folder_old, folder_new
    if table_folder and table_folder != current_folder:
        folder_data = {'folder_fix':'Y', 'folder_old':current_folder, 'folder_new':table_folder}
    else:
        folder_data = {'folder_fix':'N', 'folder_old':'', 'folder_new':''} 

    return folder_data


def groups_check(item, metatable_dict):
    '''
    Check item's group against SGID category from metatable.

    return: Dict of update info:
            {'groups_fix':'', 'groups_old':'', 'group_new':''}
    '''

    #: Get current group, wrapped in try/except for groups that error out
    try:
        current_groups = [group.title for group in item.shared_with['groups']]
    except:
        current_groups = ['Error']

    #: Get group from SGID category if in metatable
    if item.itemid in metatable_dict:
        group = get_group_from_table(metatable_dict[item.itemid])
    else:
        group = None

    #: Create groups data: groups_fix, groups_old, group_new
    if current_groups == 'Error':
        groups_data = ['N', 'Can\'t get group', '']
    elif group and group not in current_groups:
        groups_data = {'groups_fix':'Y', 'groups_old':current_groups, 'group_new':group}
    else:
        groups_data = {'groups_fix':'N', 'groups_old':'', 'group_new':''}

    return groups_data


def downloads_check(item):
    '''
    Make sure item's 'Allow others to export to different formats' box is checked

    return: Dict of update info:
            {'downloads_fix':''}
    '''

    #: Check if downloads enabled; wrap in try/except for robustness
    try:
        manager = arcgis.features.FeatureLayerCollection.fromitem(item).manager
        properties = json.loads(str(manager.properties))
    except:
        properties = None
    
    #: Create protect data: downloads_fix
    if properties and 'Extract' not in properties['capabilities']:
        fix_downloads = {'downloads_fix':'Y'}
    else:
        fix_downloads = {'downloads_fix':'N'}

    return fix_downloads


def delete_protection_check(item):
    '''
    Prevent item from being accidentally deleted.

    return: Dict of update info:
            {'delete_protection_fix':''}
    '''

    #: item.protected is Boolean
    if not item.protected:
        protect_data = {'delete_protection_fix':'Y'}
    else:
        protect_data = {'delete_protection_fix':'N'}

    return protect_data