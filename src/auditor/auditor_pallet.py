"""
auditor_pallet.py: forklift-compliant entry point
"""
from forklift.models import Pallet

from . import auditor


class AuditorPallet(Pallet):

    def requires_processing(self):
        #: No crates, run process every time
        return True

    def process(self):
        org_auditor = auditor.Auditor()
        org_auditor.check_items()
        org_auditor.fix_items()
