'''
validate.py

Usage:
    validate.py validate --org=<org> --user=<user> [--save_report=<report_path>]

Arguments:
    org           AGOL Portal to connect to [default: https://www.arcgis.com]
    user          AGOL User for authentication
    report_path   Folder to save report to, eg `c:\\temp`

Examples:
    validate.py validate --org=https://www.arcgis.com --user=me --save_report=c:\\temp
'''

from docopt import docopt

from validate import validator


def main():

    args = docopt(__doc__, version = '0.9.0')