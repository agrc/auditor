

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


def check_tags(item, tags_to_delete, uppercased_tags, articles):

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
            #: If there's already a lowercase category tag, replace it
            if category.lower() in new_tags:
                new_tags.remove(category.lower())
                new_tags.append(category)
            elif category not in new_tags:
                new_tags.append(category)
            #: Make sure it's got SGID in it's tags
            if 'SGID' not in new_tags:
                new_tags.append('SGID')

    return new_tags


def get_category_and_name(item, metatable_dict):
    #: Find item in meta table, check name

    current_itemid = item.itemid

    table_sgid_name, table_agol_name = metatable_dict[current_itemid]
    table_category = table_sgid_name.split('.')[1].proper()

    group = f'Utah SGID {table_category}'
    
    #: List of correct data for AGOL: [name, group, folder]
    new_data = [table_agol_name, group, table_category]

    return new_data
