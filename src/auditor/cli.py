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
    auditor -r -v
"""

import datetime
import logging
import socket
import sys

from io import StringIO

from docopt import docopt, DocoptExit

from supervisor.models import MessageDetails, Supervisor
from supervisor.message_handlers import EmailHandler

from .auditor import Auditor, credentials


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

        summary_logger = logging.getLogger(__name__)
        summary_logger.setLevel(logging.DEBUG)

        if args['spot']:
            #: Only dump summary to the console if verbose
            if args['--verbose']:
                cli_handler = logging.StreamHandler(stream=sys.stdout)
                cli_handler.setLevel(logging.DEBUG)
                cli_formatter = logging.Formatter(
                    fmt='%(levelname)-7s %(asctime)s %(module)10s:%(lineno)5s %(message)s', datefmt='%m-%d %H:%M:%S'
                )
                cli_handler.setFormatter(cli_formatter)
                summary_logger.addHandler(cli_handler)

            org_auditor = Auditor(summary_logger, args['--verbose'], args['ITEM'])

            if args['--dry']:
                org_auditor.check_items(args['--save_report'])
            else:
                org_auditor.check_items(report=False)  #: only do the fix report on a full run.
                org_auditor.fix_items(args['--save_report'])

            org_auditor.check_organization_wide()

        elif args['scheduled']:
            #: Create a string stream for summary report
            summary_stream = StringIO()
            summary_handler = logging.StreamHandler(stream=summary_stream)
            stream_formatter = logging.Formatter(
                fmt='<pre>%(levelname)-7s %(asctime)s %(module)10s:%(lineno)5s %(message)s</pre>',
                datefmt='%m-%d %H:%M:%S'
            )
            summary_handler.setFormatter(stream_formatter)
            summary_logger.addHandler(summary_handler)

            #: set up supervisor, add email handler
            auditor_supervisor = Supervisor(
                project_name='auditor', logger=summary_logger, log_path=credentials.REPORT_BASE_PATH
            )

            auditor_supervisor.add_message_handler(EmailHandler(credentials.EMAIL_SETTINGS))

            org_auditor = Auditor(summary_logger)
            org_auditor.check_organization_wide()
            org_auditor.check_items(report=False)  #: Don't bother reporting checks
            org_auditor.fix_items(report=True)

            #: Build and send summary message
            summary_message = MessageDetails()
            summary_message.message = summary_stream.getvalue()
            summary_message.project_name = 'auditor'
            summary_message.attachments = [credentials.REPORT_BASE_PATH]
            summary_message.subject = f'Auditor Report {datetime.datetime.today()}'

            auditor_supervisor.notify(summary_message)

        else:
            raise NotImplementedError(
                'Command not recognized. Please run either "spot" or "scheduled" audit (see help)'
            )
