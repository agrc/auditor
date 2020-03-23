import json

import arcgis
import arcpy


class ItemFixer:
    '''
    Class to fix an AGOL item that has previously been checked using
    ItemChecker. Uses the item report dictionary created by ItemChecker for the
    item to determine what needs to be fixed and what values to use.

    This class is specific to a single item. General org-level data should be
    stored in the Validate class and passed to methods if needed (like
    dictionary of groups and their ids).

    The results of each fix, or a note that a fix was not needed, are added to
    the item_report dictionary passed to the ItemFixer like thus:
    {<topic>_result: result}
    '''

    def __init__(self, item, item_report):

        self.item = item
        self.item_report = item_report


    def tags_fix(self):
        '''
        Use item.update() to update tags.

        Updates item_report with results for this fix:
        {tags_result: result}
        '''

        tags = self.item_report['tags_new']

        #: Was no update needed?
        if not tags:
            self.item_report['tags_result'] = 'No update needed for tags'
            return

        update_result = self.item.update({'tags': tags})

        #:item.update() returns False if it fails
        if not update_result:
            self.item_report['tags_result'] = f'Failed to update tags to {tags}'
            return

        self.item_report['tags_result'] = f'Updated tags to {tags}'


    def title_fix(self):
        '''
        Use item.update() to update title.

        Updates item_report with results for this fix:
        {title_result: result}
        '''

        title = self.item_report['title_new']

        #: Was no update needed?
        if not title:
            self.item_report['title_result'] = 'No update needed for title'
            return

        update_result = self.item.update({'title': title})

        #:item.update() returns False if it fails
        if not update_result:
            self.item_report['title_result'] = f'Failed to update title to "{title}"'
            return

        self.item_report['title_result'] = f'Updated title to "{title}"'


    def group_fix(self, groups_dict):
        '''
        Use item.share() to share to group
        groups_dict:    A dictionary of all the org's groups and their
                        corresponding ids.

        Updates item_report with results for this fix:
        {groups_result: result}
        '''

        #: Was no update needed?
        if self.item_report['groups_fix'].casefold() != 'y':
            self.item_report['groups_result'] = 'No update needed for grpi[s'
            return

        #: Share to everyone and groups
        group_name = self.item_report['group_new']
        try:
            gid = groups_dict[group_name]
            share_results = self.item.share(everyone=True, groups=[gid])
            result_dict = share_results['results'][0]

            #: Report if we couldn't share it with group
            if gid in result_dict['notSharedWith']:
                self.item_report['groups_result'] = f'Failed to share with everyone and "{group_name}" group'
                return

        #: Groups should always be found, but in case they're not, report
        except KeyError:
            self.item_report['groups_result'] = f'Cannot find group "{group_name}" in organization'
            return

        self.item_report['groups_result'] = f'Shared with everyone and "{group_name}" group'


    def folder_fix(self):
        '''
        Use item.move() to move item to folder.

        Updates item_report with results for this fix:
        {folder_result: result}
        '''

        #: Was no update needed?
        if self.item_report['folder_fix'].casefold() != 'y':
            self.item_report['folder_result'] = 'No update needed for folder'
            return

        #: Try the move
        folder = self.item_report['folder_new']
        move_result = self.item.move(folder)

        #: .move(folder) returns None if folder not found
        if not move_result:
            self.item_report['folder_result'] = f'"{folder}" folder not found'
            return

        #: Catching any other abnormal result
        if not move_result['success']:
            self.item_report['folder_result'] = f'Failed to move item to "{folder}" folder'
            return

        #: If all the checks have passed, return good result.
        self.item_report['folder_result'] = f'Item moved to "{folder}" folder'


    def delete_protection_fix(self):
        '''
        Use item.protect() to prevent item from being deleted.

        Updates item_report with results for this fix:
        {tags_title_result: result}
        '''

        if self.item_report['delete_protection_fix'].casefold() != 'y':
            self.item_report['delete_protection_result'] = 'No update needed for delete protection'
            return

        protect_result = self.item.protect(True)

        if not protect_result['success']:
            self.item_report['delete_protection_result'] = f'Failed to protect item'
            return

        self.item_report['delete_protection_result'] = f'Item protected'


    def downloads_fix(self):
        '''
        Create a FeatureLayerCollection from item and use it's manager object to
        allow downloads by adding 'Extract' to it's capabilities.

        Updates item_report with results for this fix:
        {downloads_result: result}
        '''

        if self.item_report['downloads_fix'].casefold() != 'y':
            self.item_report['downloads_result'] = 'No update needed for downloads'
            return

        manager = arcgis.features.FeatureLayerCollection.fromitem(self.item).manager
        properties = json.loads(str(manager.properties))

        current_capabilities = properties['capabilities']
        new_capabilities = current_capabilities + ',Extract'
        download_result = manager.update_definition({'capabilities': new_capabilities})

        if not download_result['success']:
            self.item_report['downloads_result'] = f'Failed to enable downloads'
            return

        self.item_report['downloads_result'] = f'Downloads enabled'


    def metadata_fix(self):
        '''
        Overwrite the existing AGOL metadata with the metadata from a source
        feature class using agol_item.metadata = fc_metadata.xml where
        fc_metadata is an arcpy.metadata.Metadata() object created via the
        arcpy.metadata library.

        Updates item_report with results for this fix:
        {metdata_result: result}
        '''

        if self.item_report['metadata_fix'].casefold() != 'y':
            self.item_report['metadata_result'] = 'No update needed for metadata'
            return

        fc_path = self.item_report['metadata_new']

        arcpy_metadata = arcpy.metadata.Metadata(fc_path)
        try:
            self.item.metadata = arcpy_metadata.xml

            if self.item.metadata != arcpy_metadata.xml:
                self.item_report['metadata_result'] = f'Tried to update metadata from "{fc_path}; verify manually"'
                return

        except ValueError:
            self.item_report['metadata_result'] = f'Metadata too long to upload from "{fc_path}" (>32,767 characters)'
            return

        self.item_report['metadata_result'] = f'Metadata updated from "{fc_path}"'


    def description_note_fix(self, static_note, shelved_note):
        '''
        Add static_note or shelved_note to beginning of the description field
        with a blank space before the rest of the description. static_note and
        shelved_note should be strings of properly-formatted HTML.

        Updates item_report with results for this fix:
        {description_note_result: result}
        '''

        if self.item_report['description_note_fix'].casefold() != 'y':
            self.item_report['description_note_result'] = 'No update needed for description'
            return

        source = self.item_report['description_note_source']
        new_description = self.item.description
        if source == 'shelved':
            new_description = f'{shelved_note}<div><br />{self.item.description}'
        elif source == 'static':
            new_description = f'{static_note}<div><br />{self.item.description}'

        update_result = self.item.update(item_properties={'description': new_description})

        if not update_result:
            self.item_report['description_note_result'] = f'Failed to add {source} note to description'
            return

        self.item_report['description_note_result'] = f'{source} note added to description'


    def thumbnail_fix(self):
        '''
        Overwrite the thumbnail if the item is in one of the icon groups. The
        item_report dictionary should have the path to the new thumbnail.
        '''

        if self.item_report['thumbnail_fix'].casefold() != 'y':
            self.item_report['thumbnail_result'] = 'No update needed for thumbnail'
            return

        thumbnail_path = self.item_report['thumbnail_path']
        update_result = self.item.update(thumbnail=thumbnail_path)

        if not update_result:
            self.item_report['thumbnail_result'] = f'Failed to update thumbnail from {thumbnail_path}'
            return

        self.item_report['thumbnail_result'] = f'Thumbnail updated from {thumbnail_path}'

    def authoritative_fix(self):
        '''
        Change the item.content_status to 'authoritative', 'deprecated', or
        None (to reset).

        Updates item_report with results for this fix:
        {authoritative_result: result}
        '''

        new_authoritative = self.item_report['authoritative_new']
        if self.item_report['authoritative_fix'].casefold() != 'y':
            self.item_report['authoritative_result'] = 'No update needed for content status'
            return

        try:
            self.item.content_status = new_authoritative
            self.item_report['authoritative_result'] = f'Content status updated to "{new_authoritative}"'
            return

        except ValueError:
            self.item_report['authoritative_result'] = f'Invalid new authoritative value "{new_authoritative}"'
            return

        except RuntimeError:
            self.item_report['authoritative_result'] = f'User does not have privileges to change content status. Must use an AGOL account that is assigned the Administrator role.'
            return
