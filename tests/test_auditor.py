import pytest
from unittest.mock import patch, MagicMock

from auditor.auditor import (retry, Metatable)


def test_retry():

    class CustomError(Exception):
        pass

    def inner_retry():
        if 4 % 2 == 0:
            #: If this exception gets raised, it means retry() has either not been called or has gone through all it's tries and has raised the original exception.
            raise CustomError

    with pytest.raises(CustomError):
        retry(inner_retry)


@patch(arcpy.da.SearchCursor)
def test_read_sgid_metatable():

    #: table_sgid_name, table_agol_itemid, table_agol_name, table_authoritative
    sgid_row = ['SGID.GEOSCIENCE.Minerals', '9d2e949a9492425dbb4e5d5212f9ef19', 'Utah Minerals', None]
    #: table_sgid_name, table_agol_itemid, table_agol_name, table_category
    agol_row = [
        'SGID.WATER.ParagonahStructures', 'dd7fa2d78d2547759a50d6f827f8df3a', 'Utah Paragonah Structures', 'shelved'
    ]
    sgid_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'Authoritative']
    agol_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'CATEGORY']

    # cursor_mock = unittest.MagicMock()
    # cursor_mock.__iter__.return_value = [sgid_row, agol_row]

    arcpy.da.SearchCursor = MagicMock()
    arcpy.da.SearchCursor.__inter__.return_value = [sgid_row]

    test_table = Metatable()
    test_table.read_metatable(None, [sgid_fields])

    # '9d2e949a9492425dbb4e5d5212f9ef19': ['SGID.GEOSCIENCE.Minerals', 'Utah Minerals', 'SGID', None],
    assert test_table.metatable_dict['9d2e949a9492425dbb4e5d5212f9ef19'] == [
        'SGID.GEOSCIENCE.Minerals', 'Utah Minerals', 'SGID', None
    ]
