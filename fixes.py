import arcgis
import arcpy
import json

def tags_or_title_fix(item, title=None, tags=None):
    '''
    Use item.update() to update title and/or tags.
    title:  New title as a string
    tags:   New tags as a list of strings

    return: Update results as a string
    '''

    #: Tags and title combined .update()
    update_dict = {}
    messages = []
    if title:
        update_dict['title'] = title
        messages.append(f'title to {title}')
    if tags:
        update_dict['tags'] = tags
        messages.append(f'tags to {tags}')
    update_result = item.update(update_dict)
    if update_result:
        result = f'Updated {", ".join(messages)}'
    else:
        result = f'Failed to update {", ".join(messages)}'

    return result


def group_fix(item, gid):
    '''
    Use item.share() to share to group

    return: Sharing results as a string
    '''

    #: Group
    #: We should never hit the except if we are getting the gid from an 
    #: org.groups.search() call.
    try:
        share_results = item.share(everyone=True, groups=[gid])
        result_dict = share_results['results'][0]
        if gid not in result_dict['notSharedWith']:
            result = f'Group updated to group id {gid}'
        else:
            result = f'Failed to update group to group id {gid}'

    except Exception as e:
        if 'Cannot find group with id' in str(e):
            result = f'Cannot find group with id: {gid}'
        else:
            result = str(e)

    return result


def folder_fix(item, folder):
    '''
    Use item.move() to move item to folder.

    return: Move results as a string
    '''

    #: Folder
    try:
        move_result = item.move(folder)
        if move_result['success']:
            result = f'Item moved to {folder}'
        else:
            result = f'Failed to move item to {folder}'
    except TypeError as e:
        if 'subscriptable' in str(e):
            result = f'Failed to move item to {folder}'

    return result


def delete_protection_fix(item):
    '''
    Use item.protect() to prevent item from being deleted.

    return: Protection result as a string
    '''

    #: Delete Protection
    protect_result = item.protect(True)
    if protect_result['success']:
        result = f'Item protected'
    else:
        result = f'Failed to protect item'

    return result


def downloads_fix(item):
    '''
    Create a FeatureLayerCollection from item and use it's manager object to
    allow downloads by adding 'Extract' to it's capabilities.

    return: Download enabling results as a string
    '''

    #: Enable Downloads
    manager = arcgis.features.FeatureLayerCollection.fromitem(item).manager
    properties = json.loads(str(manager.properties))

    current_capabilities = properties['capabilities']
    new_capabilities = current_capabilities + ',Extract'
    download_result = manager.update_definition({ 'capabilities': new_capabilities})

    if download_result['success']:
        result = f'Downloads enabled'
    else:
        result = f'Failed to enable downloads'

    return result


def metadata_fix(item, fc_path):


    arcpy_metadata = arcpy.metadata.Metadata(fc_path)
    try:
        item.metadata = arcpy_metadata.xml
        
        if item.metadata == arcpy_metadata.xml:
            result = f'Metadata updated from {fc_path}'
        else:
            result = f'Failed to update metadata from {fc_path}'
            
    except ValueError:
        result = f'Metadata too long to upload from {fc_path} (>32,767 characters)'



    return result