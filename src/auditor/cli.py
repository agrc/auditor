"""
auditor

Usage:
    auditor [--save_report=<dir> --dry --verbose]

Options:
    -h, --help
    -r, --save_report <dir>     Directory to save report to, e.g. `c:\\temp`
    -d, --dry                   Only run the checks, don't do any fixes [default: False]
    -v, --verbose               Print status updates to the console [default: False]

Examples:
    auditor --save_report=c:\\temp -v
"""

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

        report_dir = args['--save_report']

        org_auditor = Auditor(args['--verbose'])
        org_auditor.check_items(report_dir)

        if not args['--dry']:
            org_auditor.fix_items(report_dir)
