# Auditor 🕴️

You... are AWESOME (go watch Kurt Kuenne's short film ["Validation"](https://www.youtube.com/watch?v=Cbk980jV7Ao))

(This is a holdover from when this was named "validator", but it's too good to remove.)

![auditor_sm](https://user-images.githubusercontent.com/325813/90076350-b8c37100-dcbc-11ea-9df7-48ea21ec138a.png)

## Item Checks

`auditor` audits all the AGOL Feature Service items in a user's folders so long as the items' ids are found in either an SDE-hosted or AGOL-hosted metatable. The following AGOL item properties are checked:

* Title
* Group
* Folder
* Metadata
* Description note for shelved/static items
* Path to appropriate thumbnail image
* Sets the flag for delete protection
* Sets the flag to 'Allow others to export to different formats', which opens up GDB downloads in Open Data
* Marks the item as Authoritative

It also validates the tags (proper-case tags, don't repeat words found in the title) for *all* Feature Service items in the user's folders, regardless if they are found in the metatables or not.

### What Items Does it Check?

`auditor` checks all the Feature Service items in a user's folders. It does this by getting a list of the user's folders and then searching for any Feature Services in each folder (including the root directory).

Because a user's folder only holds items that they own, it effectively checks all the user's Feature Service items. However, be aware of the distinction of all the Feature Services in a user's folders vs all a user's Feature Services in case you run into a weird edge case.

## Installation

1. Clone the ArcGIS Pro conda environment and activate:
   * `conda create -n auditor --clone arcgispro-py3`
   * `activate auditor`
1. Clone the repository
   * `cd <my git directory>`
   * `git clone https://github.com/agrc/auditor.git`
1. Create a `credentials.py` file in the repo's directory using `credentials_template.py`.
   * DO NOT check `credentials.py` into version control! The repo's `.gitignore` has been set to ignore `credentials.py`; verify this on your local repo.
1. Install auditor:
   * `cd <my git directory>\auditor`
   * `pip install .`
   * Or, for development, `pip install -e .[tests]`

## Usage

### Command line

`python auditor [-r|--save_report -d|--dry -v|--verbose]`

Options:

* `-h`, `--help`
* `-r`, `--save_report`           Save report to the file specified in the credentials file (will be rotated)
* `-d`, `--dry`                   Only run the checks, don't do any fixes
* `-v`, `--verbose`               Print status updates to the console

Example:

* `auditor -v -r`

### Forklift

`auditor` has a forklift pallet (`src/auditor/auditor_pallet.py`) that will run both the checks and fixes and save the reports in the report directory specified in the `credentials.py` file.

## Metatable format

The SGID metatable is read using `arcpy` and should at a minimum have the three following fields:

1. `TABLENAME`: The fully-qualified source table name. The schema will be used to determine the group and folder (ie, `SGID10.BOUNDARIES.Counties`'s category is `Utah SGID Boundaries` and its folder is `Boundaries`)
1. `AGOL_ITEM_ID`: The published AGOL item id for the table.
1. `AGOL_PUBLISHED_NAME`: The table's desired AGOL Feature Service name.

The AGOL metatable is hosted on AGOL and is also read with `arcpy`. It needs the following fields in addition to the SGID metatable's fields:

1. `Category`: Whether the layer is `shelved` or `static`.

## Thumbnail Directory

The thumbnail directory specified in `credentials.py` should hold thumbnails named `group_name.png`, where `group_name` is the SGID group (in lowercase)
