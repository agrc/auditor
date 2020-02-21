import arcgis
import arcpy
import json

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


    def tags_or_title_fix(self):
        '''
        Use item.update() to update title and/or tags.

        Updates item_report with results for this fix:
        {tags_title_result: result}
        '''

        title = self.item_report['title_new']
        tags = self.item_report['tags_new']

        if title or tags:

            #: Tags and title combined .update()
            update_dict = {}
            messages = []
            if title:
                update_dict['title'] = title
                messages.append(f'title to "{title}"')
            if tags:
                update_dict['tags'] = tags
                messages.append(f'tags to {tags}')
            update_result = self.item.update(update_dict)
            if update_result:
                result = f'Updated {", ".join(messages)}'
            else:
                result = f'Failed to update {", ".join(messages)}'
        
        else:
            result = 'No update needed for title or tags'

        self.item_report['tags_title_result'] = result


    def group_fix(self, groups_dict):
        '''
        Use item.share() to share to group
        groups_dict:    A dictionary of all the org's groups and their
                        corresponding ids.

        Updates item_report with results for this fix:
        {groups_result: result}
        '''

        if self.item_report['groups_fix'] == 'Y':

            group_name = self.item_report['group_new']

            try:
                gid = groups_dict[group_name]

                share_results = self.item.share(everyone=True, groups=[gid])
                result_dict = share_results['results'][0]
                if gid not in result_dict['notSharedWith']:
                    result = f'Shared with everyone and "{group_name}" group'
                else:
                    result = f'Failed to share with everyone and "{group_name}" group'

            except KeyError:
                result = f'Cannot find group "{group_name}" in organization'

        else:
            result = 'No update needed for groups'

        self.item_report['groups_result'] = result


    def folder_fix(self):
        '''
        Use item.move() to move item to folder.

        Updates item_report with results for this fix:
        {folder_result: result}
        '''

        if self.item_report['folder_fix'] == 'Y':
            folder = self.item_report['folder_new']

            move_result = self.item.move(folder)
            if move_result:
                if move_result['success']:
                    result = f'Item moved to "{folder}" folder'
                else:
                    result = f'Failed to move item to "{folder}" folder'
            else:
                result = f'"{folder}" folder not found'

        else:
            result = 'No update needed for folder'

        self.item_report['folder_result'] = result


    def delete_protection_fix(self):
        '''
        Use item.protect() to prevent item from being deleted.

        Updates item_report with results for this fix:
        {tags_title_result: result}
        '''

        if self.item_report['delete_protection_fix'] == 'Y':

            protect_result = self.item.protect(True)
            if protect_result['success']:
                result = f'Item protected'
            else:
                result = f'Failed to protect item'

        else:
            result = 'No update needed for delete protection'

        self.item_report['delete_protection_result'] = result


    def downloads_fix(self):
        '''
        Create a FeatureLayerCollection from item and use it's manager object to
        allow downloads by adding 'Extract' to it's capabilities.

        Updates item_report with results for this fix:
        {downloads_result: result}
        '''

        if self.item_report['downloads_fix'] == 'Y':
                
            manager = arcgis.features.FeatureLayerCollection.fromitem(self.item).manager
            properties = json.loads(str(manager.properties))

            current_capabilities = properties['capabilities']
            new_capabilities = current_capabilities + ',Extract'
            download_result = manager.update_definition({ 'capabilities': new_capabilities})

            if download_result['success']:
                result = f'Downloads enabled'
            else:
                result = f'Failed to enable downloads'

        else:
            result = 'No update needed for downloads'

        self.item_report['downloads_result'] = result


    def metadata_fix(self):
        '''
        Overwrite the existing AGOL metadata with the metadata from a source
        feature class using agol_item.metadata = fc_metadata.xml where
        fc_metadata is an arcpy.metadata.Metadata() object created via the
        arcpy.metadata library.

        Updates item_report with results for this fix:
        {metdata_result: result}        
        '''
        if self.item_report['metadata_fix'] == 'Y':
            fc_path = self.item_report['metadata_new']

            arcpy_metadata = arcpy.metadata.Metadata(fc_path)
            try:
                self.item.metadata = arcpy_metadata.xml
                
                if self.item.metadata == arcpy_metadata.xml:
                    result = f'Metadata updated from "{fc_path}"'
                else:
                    result = f'Failed to update metadata from "{fc_path}"'
                    
            except ValueError:
                result = f'Metadata too long to upload from "{fc_path}" (>32,767 characters)'
        
        else:
            result = 'No update needed for metadata'

        self.item_report['metadata_result'] = result