

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


def tags_check(item, tags_to_delete, uppercased_tags, articles):

    #: Keep track of groups that fail
    failed_group_items = []
    
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
        if orig_tag in item.title.split():
            single_word_tag_in_title = True
        #: multi-word tag in title
        multi_word_tag_in_title = False
        if ' ' in orig_tag and orig_tag in item.title:
            multi_word_tag_in_title = True

        #: operate on lower case to fix any weird mis-cased tags
        lowercase_tag = orig_tag.lower()

        #: Run checks on the tags. A check that modifies the tag should
        #: append it to new_tags. A check that removes unwanted tags
        #: should just pass. If a tag passes all the checks, it gets
        #: properly cased and added to new_tags (the else clause).

        #: Fix/keep 'Utah' if it's not in the title
        if lowercase_tag == 'utah' and orig_tag not in item.title.split():
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
    
    #: Add the category tag
    groups = []
    #: Wrap in try/except because some groups fail for some odd reason
    try:
        for g in item.shared_with['groups']:
            groups.append(g.title)
    except:
        failed_group_items.append(item.title)

    for group in groups:
        if 'Utah SGID' in group:
            category = group.split('Utah SGID ')[-1]
            #: If there's already a lowercase tag for the category, replace it
            if category.lower() in new_tags:
                new_tags.remove(category.lower())
                new_tags.append(category)
            elif category not in new_tags:
                new_tags.append(category)
            #: Make sure it's got SGID in it's tags
            if 'SGID' not in new_tags:
                new_tags.append('SGID')

    #: Create tags data: [fix_tags, old_tags, new_tags]
    #: Tag lists are joined into a single string with '; ' for reporting
    if sorted(new_tags) != sorted(item.tags):
        tags_data = ['Y', '; '.join(item.tags), '; '.join(new_tags)]
    else:
        tags_data = ['N', '', '']

    return tags_data


def get_category_and_name(item, metatable_dict):
    #: Find item in meta table, check name

    current_itemid = item.itemid

    #: Only do check if it's in the metatable; otherwise, return ['Not SGID'x3]
    if current_itemid in metatable_dict:
        table_sgid_name, table_agol_name = metatable_dict[current_itemid]
        table_category = table_sgid_name.split('.')[1].title()

        group = f'Utah SGID {table_category}'
        
        #: List of correct data for AGOL: [name, group, folder]
        new_data = [table_agol_name, group, table_category]

    else:
        new_data = ['Not SGID', 'Not SGID', 'Not SGID']

    return new_data


def title_check(item, metatable_dict):

    #: Get title from metatable if it's in the table
    if item.itemid in metatable_dict:
        table_agol_title = metatable_dict[item.itemid][1]
    else:
        table_agol_title = None

    #: Create title data: [fix_title, old_title, new_title]
    #: Always include the old title for readability
    if table_agol_title and table_agol_title != item.title:
        title_data = ['Y', item.title, table_agol_title]
    else:
        title_data = ['N', item.title, '']  

    return title_data


def folder_check(item, metatable_dict, itemid_and_folder):

    #: Get current folder from dictionary of items' folders
    current_folder = itemid_and_folder[item.itemid]

    #: Get folder from SGID category if in metatable
    if item.itemid in metatable_dict:
        SGID_name = metatable_dict[item.itemid][0]
        table_folder = SGID_name.split('.')[1].title()
    else:
        table_folder = None

    #: Create folder data: [fix_folder, old_folder, new_folder]
    if table_folder and table_folder != current_folder:
        folder_data = ['Y', current_folder, table_folder]
    else:
        folder_data = ['N', '', ''] 

    return folder_data


def groups_check(item, metatable_dict):
    
    #: Get current group, wrapped in try/except for groups that error out
    try:
        current_groups = [group.title for group in item.shared_with['groups']]
    except:
        current_groups = ['Error']

    #: Get group from SGID category if in metatable
    if item.itemid in metatable_dict:
        SGID_name = metatable_dict[item.itemid][0]
        table_category = SGID_name.split('.')[1].title()
        group = f'Utah SGID {table_category}'
    else:
        group = None

    #: Create groups data: [fix_groups, old_groups, new_group]
    if current_groups == 'Error':
        groups_data = ['N', 'Can\'t get group', '']
    elif group and group not in current_groups:
        groups_data = ['Y', '; '.join(current_groups), group]
    else:
        groups_data = ['N', '', '']

    return groups_data


def downloads_check(item):
    
    #: Check if downloads enabled; wrap in try/except for robustness
    try:
        manager = arcgis.features.FeatureLayerCollection.fromitem(item).manager
        properties = json.loads(str(manager.properties))
    except:
        properties = None
    
    #: Create protect data: [fix_downloads]
    if properties and 'Extract' not in properties['capabilities']:
        fix_downloads = ['Y']
    else:
        fix_downloads = ['N']

    return fix_downloads


def delete_protection_check(item):
    
    #: item.protected is Boolean
    if not item.protected:
        protect_data = ['Y']
    else:
        protect_data = ['N']

    return protect_data