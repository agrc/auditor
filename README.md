# agol-validator

You... are AWESOME (go watch Kurt Kuenne's short film ["Validation"](https://www.youtube.com/watch?v=Cbk980jV7Ao))

## Item Checks

`agol-validator` validates all the AGOL Feature Service items in a user's folders based on information in a metatable:

* Title
* Group
* Folder

It also applies some checks irrespective of a table:

* Tags: proper-cases tags, doesn't repeat words found in the title
* Sets the flag for delete protection
* Sets the flag to 'Allow others to export to different formats', which opens up GDB downloads in Open Data.

#### Metatable format

The metatable is read using `arcpy` and should at a minimum have the three following fields:

1. `TABLENAME`: The fully-qualified source table name. The schema will be used to determine the group and folder (ie, `SGID10.BOUNDARIES.Counties`'s category is `Utah SGID Boundaries` and its folder is `Boundaries`)
1. `AGOL_ITEM_ID`: The published AGOL item id for the table.
1. `AGOL_PUBLISHED_NAME`: The table's desired AGOL Feature Service name.

#### What Items Does it Check?

`agol_validator` checks all the Feature Service items in a user's folders. It does this by getting a list of the user's folders and then searching for any Feature Services in each folder (including the root directory).

Because a user's folder only holds items that they own, it effectively checks all the user's Feature Service items. However, be aware of the distinction of all the Feature Services in a user's folders vs all a user's Feature Services in case you run into a weird edge case.

## Environment

1. Clone the ArcGIS Pro conda environment:
   - `conda create --clone arcgispro-py3 --name validator`
1. Activate the new environment:
   - `activate validator`
1. Install the needed conda packages (`docopt`):
   - `conda install --file requirements.txt`
