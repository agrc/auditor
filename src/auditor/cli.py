"""
auditor

Usage:
    auditor spot [--save_report --dry --verbose ITEM ...]
    auditor scheduled

Options:
    -h, --help
    -r, --save_report           Save report to the file specified in the credentials file (will be rotated)
    -d, --dry                   Only run the checks, don't do any fixes [default: False]
    -v, --verbose               Print status updates to the console [default: False]
    ITEM                        One or more AGOL item IDs to audit. If none are specified, all items are audited.

Examples:
    auditor spot -r -v
    auditor spot -v -r aaaaaaaabbbbccccddddeeeeeeeeeeee
    auditor scheduled
"""

import datetime
import logging
import sys

from io import StringIO

from docopt import docopt, DocoptExit

from supervisor.models import MessageDetails, Supervisor
from supervisor.message_handlers import SendGridHandler

from .auditor import Auditor, credentials


def cli():
    """Main entry point for auditor; parses args using docopt"""

    #: try/except/else to print help if bad input received
    try:
        args = docopt(__doc__, version='1.0')
    except DocoptExit:
        print('\n*** Invalid input ***\n')
        print(__doc__)
    else:

        #: Logger that will gather the summary information.
        summary_logger = logging.getLogger(__name__)
        summary_logger.setLevel(logging.DEBUG)

        if args['spot']:

            #: Only dump summary info to the console if verbose
            #: Note: currently, org-wide checks (duplicate names) only reported if verbose
            if args['--verbose']:
                cli_handler = logging.StreamHandler(stream=sys.stdout)
                cli_handler.setLevel(logging.DEBUG)
                cli_formatter = logging.Formatter(
                    fmt='%(levelname)-7s %(asctime)s %(module)10s:%(lineno)5s %(message)s', datefmt='%m-%d %H:%M:%S'
                )
                cli_handler.setFormatter(cli_formatter)
                summary_logger.addHandler(cli_handler)

            #: Set up org, check & fix items
            org_auditor = Auditor(summary_logger, args['--verbose'], args['ITEM'])
            if args['--dry']:
                org_auditor.check_items(args['--save_report'])
            else:
                org_auditor.check_items(report=False)  #: only do the fix report on a full run.
                org_auditor.fix_items(args['--save_report'])
            org_auditor.check_organization_wide()

            return

        if args['scheduled']:

            #: Create a string stream for summary report
            summary_stream = StringIO()
            summary_handler = logging.StreamHandler(stream=summary_stream)
            stream_formatter = logging.Formatter(
                fmt='%(levelname)-7s %(asctime)s %(module)10s:%(lineno)5s %(message)s', datefmt='%m-%d %H:%M:%S'
            )
            summary_handler.setFormatter(stream_formatter)
            summary_logger.addHandler(summary_handler)

            #: set up supervisor, add email handler
            auditor_supervisor = Supervisor(logger=summary_logger, log_path=credentials.REPORT_BASE_PATH)
            auditor_supervisor.add_message_handler(
                SendGridHandler(credentials.SENDGRID_SETTINGS, project_name='auditor')
            )

            #: Set up org, check & fix items
            org_auditor = Auditor(summary_logger)
            org_auditor.check_organization_wide()
            org_auditor.check_items(report=False)  #: Checks will be reported in fix report
            org_auditor.fix_items(report=True)

            #: Build and send summary message
            summary_message = MessageDetails()
            summary_message.message = summary_stream.getvalue()
            summary_message.attachments = [credentials.REPORT_BASE_PATH]
            summary_message.subject = f'Auditor Report {datetime.datetime.today()}'

            auditor_supervisor.notify(summary_message)
