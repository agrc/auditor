import pytest
import logging

from collections import namedtuple

from auditor.auditor import Auditor, retry, Metatable


def test_retry():

    class CustomError(Exception):
        pass

    def inner_retry():
        if True:
            #: If this exception gets raised, it means retry() has either not been called or has gone through all it's tries and has raised the original exception.
            raise CustomError

    with pytest.raises(CustomError):
        retry(inner_retry)


def test_read_sgid_metatable_to_dictionary(mocker):

    def return_sgid_row(self, table, fields):
        #: table_sgid_name, table_agol_itemid, table_agol_name, table_authoritative
        for row in [['table name', '9d2e949a9492425dbb4e5d5212f9ef19', 'agol title', None]]:
            yield row

    sgid_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'Authoritative']

    mocker.patch('auditor.auditor.Metatable._cursor_wrapper', return_sgid_row)

    test_table = Metatable()
    test_table.read_metatable('something', sgid_fields)

    # '9d2e949a9492425dbb4e5d5212f9ef19': ['SGID.GEOSCIENCE.Minerals', 'Utah Minerals', 'SGID', None],
    assert test_table.metatable_dict['9d2e949a9492425dbb4e5d5212f9ef19'] == ['table name', 'agol title', 'SGID', None]


def test_read_agol_metatable_to_dictionary(mocker):

    def return_agol_row(self, table, fields):
        #: table_sgid_name, table_agol_itemid, table_agol_name, table_category
        for row in [['table name', 'dd7fa2d78d2547759a50d6f827f8df3a', 'agol title', 'shelved']]:
            yield row

    agol_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'CATEGORY']

    mocker.patch('auditor.auditor.Metatable._cursor_wrapper', return_agol_row)

    test_table = Metatable()
    test_table.read_metatable('something', agol_fields)

    assert test_table.metatable_dict['dd7fa2d78d2547759a50d6f827f8df3a'] == ['table name', 'agol title', 'shelved', 'n']


def test_magic_string_itemid_not_added_to_dictionary(mocker):

    def return_sgid_row(self, table, fields):
        #: table_sgid_name, table_agol_itemid, table_agol_name, table_authoritative
        for row in [['table name', 'magic_word', 'agol title', None]]:
            yield row

    sgid_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'Authoritative']

    mocker.patch('auditor.auditor.Metatable._cursor_wrapper', return_sgid_row)

    test_table = Metatable()
    test_table.read_metatable('something', sgid_fields)

    #: metatable dict should be empty
    assert test_table.metatable_dict == {}


def test_blank_itemid_not_added_to_dictionary(mocker):

    def return_sgid_row(self, table, fields):
        #: table_sgid_name, table_agol_itemid, table_agol_name, table_authoritative
        for row in [['table name', '', 'agol title', None]]:
            yield row

    sgid_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'Authoritative']

    mocker.patch('auditor.auditor.Metatable._cursor_wrapper', return_sgid_row)

    test_table = Metatable()
    test_table.read_metatable('something', sgid_fields)

    #: metatable dict should be empty
    assert test_table.metatable_dict == {}


def test_duplicate_itemids_in_same_table_reported_in_list(mocker):

    def return_sgid_row(self, table, fields):
        #: table_sgid_name, table_agol_itemid, table_agol_name, table_authoritative
        for row in [['first table name', '9d2e949a9492425dbb4e5d5212f9ef19', 'first agol title', None],
                    ['second name', '9d2e949a9492425dbb4e5d5212f9ef19', 'second title', None]]:
            yield row

    sgid_fields = ['TABLENAME', 'AGOL_ITEM_ID', 'AGOL_PUBLISHED_NAME', 'Authoritative']

    mocker.patch('auditor.auditor.Metatable._cursor_wrapper', return_sgid_row)

    test_table = Metatable()
    test_table.read_metatable('something', sgid_fields)

    #: Our duplicate id should be the only entry in .duplicate_keys and .metatable_dict should just have first item
    assert test_table.duplicate_keys == ['9d2e949a9492425dbb4e5d5212f9ef19']
    assert test_table.metatable_dict['9d2e949a9492425dbb4e5d5212f9ef19'] == [
        'first table name', 'first agol title', 'SGID', None
    ]


def test_duplicate_itemids_from_different_tables_reported_in_list(mocker):

    def return_sgid_row(self, table, fields):
        #: table_sgid_name, table_agol_itemid, table_agol_name, table_authoritative
        for row in [['sgid table name', '9d2e949a9492425dbb4e5d5212f9ef19', 'sgid agol title', None]]:
            yield row

    def return_agol_row(self, table, fields):
        #: table_sgid_name, table_agol_itemid, table_agol_name, table_category
        for row in [['agol table name', '9d2e949a9492425dbb4e5d5212f9ef19', 'agol title', 'shelved']]:
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
        'sgid table name', 'sgid agol title', 'SGID', None
    ]


def test_org_checker_completes_and_logs(mocker, caplog):

    cli_logger = logging.getLogger('test')

    agol_item = namedtuple('agol_item', ['title', 'itemid'])
    item_list = [agol_item('foo', 1), agol_item('foo', 2)]

    mocker.patch('auditor.auditor.Auditor.setup')
    
    test_auditor = Auditor(cli_logger, verbose=True)
    test_auditor.items_to_check = item_list
    with caplog.at_level(logging.DEBUG, logger='test'):
        test_auditor.check_organization_wide()

        assert 'check_for_duplicate_titles results (1):' in caplog.text
        assert 'foo: [1, 2]' in caplog.text

def test_org_checker_reports_no_results(mocker, caplog):

    cli_logger = logging.getLogger('test')

    agol_item = namedtuple('agol_item', ['title', 'itemid'])
    item_list = [agol_item('foo', 1), agol_item('bar', 2)]

    mocker.patch('auditor.auditor.Auditor.setup')
    
    test_auditor = Auditor(cli_logger, verbose=True)
    test_auditor.items_to_check = item_list
    with caplog.at_level(logging.DEBUG, logger='test'):
        test_auditor.check_organization_wide()

        assert 'check_for_duplicate_titles returned no results' in caplog.text
