import pytest

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


def test_read_sgid_metatable(mocker):

    def return_sgid_row(self, table, fields):
        #: table_sgid_name, table_agol_itemid, table_agol_name, table_authoritative
        for row in [['SGID.GEOSCIENCE.Minerals', '9d2e949a9492425dbb4e5d5212f9ef19', 'Utah Minerals', None]]:
            yield row

    sgid_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'Authoritative']

    mocker.patch('auditor.auditor.Metatable._cursor_wrapper', return_sgid_row)

    test_table = Metatable()
    test_table.read_metatable('something', sgid_fields)

    # '9d2e949a9492425dbb4e5d5212f9ef19': ['SGID.GEOSCIENCE.Minerals', 'Utah Minerals', 'SGID', None],
    assert test_table.metatable_dict['9d2e949a9492425dbb4e5d5212f9ef19'] == [
        'SGID.GEOSCIENCE.Minerals', 'Utah Minerals', 'SGID', None
    ]


def test_read_agol_metatable(mocker):

    def return_agol_row(self, table, fields):
        #: table_sgid_name, table_agol_itemid, table_agol_name, table_category
        for row in [[
            'SGID.WATER.ParagonahStructures', 'dd7fa2d78d2547759a50d6f827f8df3a', 'Utah Paragonah Structures', 'shelved'
        ]]:
            yield row

    agol_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'CATEGORY']

    mocker.patch('auditor.auditor.Metatable._cursor_wrapper', return_agol_row)

    test_table = Metatable()
    test_table.read_metatable('something', agol_fields)

    assert test_table.metatable_dict['dd7fa2d78d2547759a50d6f827f8df3a'] == [
        'SGID.WATER.ParagonahStructures', 'Utah Paragonah Structures', 'shelved', 'n'
    ]


def test_magic_word_in_itemid_field(mocker):

    def return_sgid_row(self, table, fields):
        #: table_sgid_name, table_agol_itemid, table_agol_name, table_authoritative
        for row in [['SGID.GEOSCIENCE.Minerals', 'magic_word', 'Utah Minerals', None]]:
            yield row

    sgid_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'Authoritative']

    mocker.patch('auditor.auditor.Metatable._cursor_wrapper', return_sgid_row)

    test_table = Metatable()
    test_table.read_metatable('something', sgid_fields)

    #: metatable dict should be empty
    assert test_table.metatable_dict == {}


def test_blank_itemid(mocker):

    def return_sgid_row(self, table, fields):
        #: table_sgid_name, table_agol_itemid, table_agol_name, table_authoritative
        for row in [['SGID.GEOSCIENCE.Minerals', '', 'Utah Minerals', None]]:
            yield row

    sgid_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'Authoritative']

    mocker.patch('auditor.auditor.Metatable._cursor_wrapper', return_sgid_row)

    test_table = Metatable()
    test_table.read_metatable('something', sgid_fields)

    #: metatable dict should be empty
    assert test_table.metatable_dict == {}


def test_duplicate_itemids(mocker):

    def return_sgid_row(self, table, fields):
        #: table_sgid_name, table_agol_itemid, table_agol_name, table_authoritative
        for row in [['SGID.GEOSCIENCE.Minerals', '9d2e949a9492425dbb4e5d5212f9ef19', 'Utah Minerals', None],
                    ['SGID.GEOSCIENCE.MineralsCopy', '9d2e949a9492425dbb4e5d5212f9ef19', 'Utah Minerals Copy', None]]:
            yield row

    sgid_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'Authoritative']

    mocker.patch('auditor.auditor.Metatable._cursor_wrapper', return_sgid_row)

    test_table = Metatable()
    test_table.read_metatable('something', sgid_fields)

    #: Our duplicate id should be the only entry in .duplicate_keys and .metatable_dict should just have first item
    assert test_table.duplicate_keys == ['9d2e949a9492425dbb4e5d5212f9ef19']
    assert test_table.metatable_dict['9d2e949a9492425dbb4e5d5212f9ef19'] == [
        'SGID.GEOSCIENCE.Minerals', 'Utah Minerals', 'SGID', None
    ]


def test_duplicate_itemids_from_different_tables(mocker):

    def return_sgid_row(self, table, fields):
        #: table_sgid_name, table_agol_itemid, table_agol_name, table_authoritative
        for row in [['SGID.GEOSCIENCE.Minerals', '9d2e949a9492425dbb4e5d5212f9ef19', 'Utah Minerals', None]]:
            yield row

    def return_agol_row(self, table, fields):
        #: table_sgid_name, table_agol_itemid, table_agol_name, table_category
        for row in [[
            'SGID.WATER.ParagonahStructures', '9d2e949a9492425dbb4e5d5212f9ef19', 'Utah Paragonah Structures', 'shelved'
        ]]:
            yield row

    sgid_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'Authoritative']
    agol_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'CATEGORY']

    mocker.patch('auditor.auditor.Metatable._cursor_wrapper', return_sgid_row)

    test_table = Metatable()
    test_table.read_metatable('something', sgid_fields)

    mocker.patch('auditor.auditor.Metatable._cursor_wrapper', return_agol_row)
    test_table.read_metatable('agol something', agol_fields)

    #: Our duplicate id should be the only entry in .duplicate_keys and .metatable_dict should just have first item
    assert test_table.duplicate_keys == ['9d2e949a9492425dbb4e5d5212f9ef19']
    assert test_table.metatable_dict['9d2e949a9492425dbb4e5d5212f9ef19'] == [
        'SGID.GEOSCIENCE.Minerals', 'Utah Minerals', 'SGID', None
    ]
