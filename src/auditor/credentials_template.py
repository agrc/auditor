"""
credentials_template.py: An example template of all the credentials and settings that need to be set.
"""
ORG = ''  #: URL to AGOL organization (https://www.arcgis.com)
USERNAME = ''  #: User whose items will be audited
PASSWORD = ''  #: USERNAME's password
DB = ''  #: Full path to sde connection file
THUMBNAIL_DIR = ''  #: Directory with thumbnails named sgid_group.png
METATABLE = ''  #: Full path to SGID.META.AGOLItems metatable
AGOL_TABLE = ''  #: URL for Feature Service REST endpoint for AGOL-hosted metatable
XML_TEMPLATE = ''  #: Path to 'exact copy of.xslt' template
REPORT_BASE_PATH = ''  #: File path for report CSVs of everything that was fixed; rotated on each run
