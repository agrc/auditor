import arcgis

def tags_or_title_fix(item, title=None, tags=None):
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


def group_fix(item, group):
    #: Group
    share_results = item.share(everyone=True, groups=[group])
    success = share_results['results'][0]['success']
    if success:
        result = f'Group updated to {group}'
    else:
        result = f'Failed to update group to {group}'

    return result


def folder_fix(item, folder):
    #: Folder
    move_result = item.move(folder)
    if move_result['success']:
        result = f'Item moved to {folder}'
    else:
        result = f'Failed to move item to {folder}'

    return result


def delete_protection_fix(item):
    #: Delete Protection
    protect_result = item.protect(True)
    if protect_result['success']:
        result = f'Item protected'
    else:
        result = f'Failed to protect item'

    return result


def downloads_fix(item):
    #: Enable Downloads
    manager = arcgis.features.FeatureLayerCollection.fromitem(item).manager
    download_result = manager.update_definition({ 'capabilities': 'Query,Extract' })
    if download_result['success']:
        result = f'Downloads enabled'
    else:
        result = f'Failed to enable downloads'

    return result