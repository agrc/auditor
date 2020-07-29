from forklift.models import Pallet

from . import validate

class ValidatePallet(Pallet):
    def requires_processing(self):
        #: No crates, run process every time
        return True

    def process():
        validator = validate.Validator()
        validator.check_items()
        validator.fix_items()