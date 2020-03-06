'''
agol-validator

Usage:
    agol-validator --org=<org> --user=<user> [--save_report=<report_dir> --dry --verbose]

Options:
    --org <org>                 AGOL Portal to connect to [default: https://www.arcgis.com]
    --user <user>               AGOL User for authentication
    --report_dir <report_dir>   Folder to save report to, eg `c:\\temp`
    --dry                       Only run the checks, don't do any fixes [default: False]
    --verbose                   Print status updates to the console [default: False]


Examples:
    agol-validator --org=https://www.arcgis.com --user=me --save_report=c:\\temp
'''

from docopt import docopt

from validate import Validator


def main():

    args = docopt(__doc__, version = '1.0')

    org = args['org']
    username = args['user']

    report_dir = args['report_dir']
    
    if args['dry']:
        dry = True
    else:
        dry = False
    
    if args['verbose']:
        verbose = True
    else:
        verbose = False


    org_validator = Validator(org, username, verbose)
    org_validator.check_items(report_dir)
    if not dry:
        org_validator.fix_items(report_dir)


if __name__ == '__main__':
    main()