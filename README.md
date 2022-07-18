# Auditor 🕴️

You... are AWESOME (go watch Kurt Kuenne's short film ["Validation"](https://www.youtube.com/watch?v=Cbk980jV7Ao))

(This is a holdover from when this was named "validator", but it's too good to remove.)

![auditor_sm](https://user-images.githubusercontent.com/325813/90076350-b8c37100-dcbc-11ea-9df7-48ea21ec138a.png)

## Item Checks

`auditor` audits AGOL Feature Service items based on information from either an SDE-hosted or AGOL-hosted metatable using the AGOL Item ID as a lookup key. The following item properties are checked using information from the metatable(s):

* Title
* Group
* Folder
* Metadata
* Description note for shelved/static items
* Path to appropriate thumbnail image
* Sets the flag for delete protection
* Sets the flag to 'Allow others to export to different formats', which opens up GDB downloads in Open Data
* Marks the item as Authoritative

Additionally, it also checks the tags (proper-case tags, remove unnecessary tags) regardless if the item(s) are found in the metatables or not.

### What Items Does it Check?

`auditor` will either check the items specified on the command line, or if none are specified it will check all the Feature Service items in a user's folders. It does this by getting a list of the user's folders and then searching for any Feature Services in each folder (including the root directory).

Because a user's folder only holds items that they own, it effectively checks all the user's Feature Service items. However, be aware of the distinction of all the Feature Services in a user's folders vs all a user's Feature Services in case you run into a weird edge case.

## Installation

1. Clone the ArcGIS Pro conda environment and activate:
   * `conda create -n auditor --clone arcgispro-py3`
   * `activate auditor`
1. Clone the repository
   * `cd <my git directory>`
   * `git clone https://github.com/agrc/auditor.git`
1. Create a `credentials.py` file in the auditor directory using `credentials_template.py`.
   * DO NOT check `credentials.py` into version control! The repo's `.gitignore` has been set to ignore `credentials.py`; verify this on your local repo.
1. Install auditor:
   * `cd <my git directory>\auditor`
   * `pip install -e .`
     * For some reason, you MUST use `-e`. See [https://github.com/agrc/auditor/issues/68](https://github.com/agrc/auditor/issues/68)
1. (Optional) Create a scheduled task
   * Use `scheduled_audit.bat` to run a full scheduled audit
   * Currently set for 6:00 a.m. every day.

## Usage

### Command line

``` python
python auditor spot [-r|--save_report -d|--dry -v|--verbose ITEM ...]
python auditor scheduled
```

`spot`: Run a spot audit using options below.

`scheduled`: Run a full audit, including sending notifications via supervisor and saving the report.

Options:

* `-h`, `--help`
* `-r`, `--save_report`           Save report to the file specified in the credentials file (will be rotated)
* `-d`, `--dry`                   Only run the checks, don't do any fixes
* `-v`, `--verbose`               Print status updates to the console
* `ITEM`                          One or more AGOL item IDs to audit. If none are specified, all items are audited.

Example:

* `auditor spot -vr`
* `auditor spot -v -r aaaaaaaabbbbccccddddeeeeeeeeeeee`
* `auditor scheduled`

## Metatable format

The SGID metatable is read using `arcpy` and should at a minimum have the three following fields:

1. `TABLENAME`: The fully-qualified source table name. The schema will be used to determine the group and folder (ie, `SGID10.BOUNDARIES.Counties`'s category is `Utah SGID Boundaries` and its folder is `Boundaries`)
1. `AGOL_ITEM_ID`: The published AGOL item id for the table.
1. `AGOL_PUBLISHED_NAME`: The table's desired AGOL Feature Service name.
1. `Authoritative`: Whether the dataset should be marked as "Authoritative" (`y`), "Deprecated" (`d`), or neither (blank).

The AGOL metatable is hosted on AGOL and is also read with `arcpy`. It does not contain the `Authoritative` field, and it needs the following field in addition to the SGID metatable's fields:

1. `CATEGORY`: Whether the layer is `shelved` or `static`.

## Thumbnails

The repo's `thumbnails` directory hold thumbnails named `group_name.png`, where `group_name` is the SGID group (in lowercase).
