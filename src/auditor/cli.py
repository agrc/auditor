"""
auditor

Usage:
    auditor [--save_report --dry --verbose ITEM ...]

Options:
    -h, --help
    -r, --save_report           Save report to the file specified in the credentials file (will be rotated)
    -d, --dry                   Only run the checks, don't do any fixes [default: False]
    -v, --verbose               Print status updates to the console [default: False]
    ITEM                        One or more AGOL item IDs to audit. If none are specified, all items are audited.

Examples:
    auditor -r -v
"""

import logging
import sys

from docopt import docopt, DocoptExit

from .auditor import Auditor


def cli():
    """
    Main command-line entry point for auditor; instantiates Auditor
    object, calls its check_items() method, and then calls its fix_items() if
    --dry flag is not set.
    """

    #: try/except/else to print help if bad input received
    try:
        args = docopt(__doc__, version='1.0')
    except DocoptExit:
        print('\n*** Invalid input ***\n')
        print(__doc__)
    else:

        # report_dir = args['--save_report']

        cli_logger = logging.getLogger('auditor')
        cli_logger.setLevel(logging.DEBUG)
        detailed_formatter = logging.Formatter(
            fmt='%(levelname)-7s %(asctime)s %(module)10s:%(lineno)5s %(message)s', datefmt='%m-%d %H:%M:%S'
        )
        cli_handler = logging.StreamHandler(stream=sys.stdout)
        cli_handler.setLevel(logging.DEBUG)
        cli_handler.setFormatter(detailed_formatter)
        cli_logger.addHandler(cli_handler)

        org_auditor = Auditor(cli_logger, args['--verbose'], args['ITEM'])

        org_auditor.check_organization_wide()
        if args['--dry']:
            org_auditor.check_items(args['--save_report'])
        else:
            org_auditor.check_items(report=False)  #: only do the fix report on a full run.
            org_auditor.fix_items(args['--save_report'])
