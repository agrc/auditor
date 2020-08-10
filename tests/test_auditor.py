import pytest

from auditor.auditor import retry


def test_retry():

    class CustomError(Exception):
        pass

    def inner_retry():
        if 4 % 2 == 0:
            #: If this exception gets raised, it means retry() has either not been called or has gone through all it's tries and has raised the original exception.
            raise CustomError

    with pytest.raises(CustomError):
        retry(inner_retry)
