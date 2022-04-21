# import arcgis

import unittest

from collections import namedtuple
from pathlib import Path

from auditor import credentials
from auditor import checks
from auditor.models import Auditor

# @pytest.fixture
# def agol_item():
#     import arcgis
#     org = arcgis.gis.GIS(credentials.ORG, credentials.USERNAME, credentials.PASSWORD)
#     item = org.content.get('d2ea8eb22aa64d22800bc370bb1b128b')
#     return item

# @pytest.fixture
# def metatable_dict():
#     fake_metatable = {
#         'd2ea8eb22aa64d22800bc370bb1b128b':
#             ['SGID.WATER.Stations',
#             'Utah AGOL Upload Test',
#             'SGID',
#             'y']
#         }

#     return fake_metatable


class TestTagCheck:

    def test_agrc_removed_from_tags(self, mocker):
        item_checker = mocker.Mock()
        item_checker.title_from_metatable = 'Utah Foo'
        item_checker.item.tags = ['AGRC', 'Bar']
        item_checker.new_tags = []
        item_checker.results_dict = {}
        item_checker.arcpy_metadata = False
        item_checker.new_group = False

        checks.ItemChecker.tags_check(item_checker, Auditor.tags_to_delete, Auditor.uppercased_tags, Auditor.articles)

        assert item_checker.results_dict == {'tags_fix': 'Y', 'tags_old': ['AGRC', 'Bar'], 'tags_new': ['Bar']}

    def test_ugrc_added_to_tags_for_sgid_group_item(self, mocker):
        item_checker = mocker.Mock()
        item_checker.title_from_metatable = 'Utah Foo'
        item_checker.item.tags = []
        item_checker.new_tags = []
        item_checker.results_dict = {}
        item_checker.arcpy_metadata = False
        item_checker.new_group = 'Utah SGID Bar'

        checks.ItemChecker.tags_check(item_checker, Auditor.tags_to_delete, Auditor.uppercased_tags, Auditor.articles)

        assert item_checker.results_dict == {'tags_fix': 'Y', 'tags_old': [], 'tags_new': ['Bar', 'SGID', 'UGRC']}

    def test_agrc_removed_ugrc_added_to_tags(self, mocker):
        item_checker = mocker.Mock()
        item_checker.title_from_metatable = 'Utah Foo'
        item_checker.item.tags = ['AGRC', 'Bar']
        item_checker.new_tags = []
        item_checker.results_dict = {}
        item_checker.arcpy_metadata = False
        item_checker.new_group = 'Utah SGID Bar'

        checks.ItemChecker.tags_check(item_checker, Auditor.tags_to_delete, Auditor.uppercased_tags, Auditor.articles)

        assert item_checker.results_dict == {
            'tags_fix': 'Y',
            'tags_old': ['AGRC', 'Bar'],
            'tags_new': ['Bar', 'SGID', 'UGRC']
        }


class TestGroupFromTable:

    def test_get_group_from_table_shelved_item(self):
        metable_row = ('SGID.Foo.Bar', '', 'shelved', '')

        group = checks.get_group_from_table(metable_row)

        assert group == 'UGRC Shelf'

    def test_get_group_from_table_sgid_item(self):
        metable_row = ('SGID.Foo.Bar', '', '', '')

        group = checks.get_group_from_table(metable_row)

        assert group == 'Utah SGID Foo'


class TestSetup:

    def test_setup_sets_shelved_folder(self, mocker):
        item_checker = mocker.Mock()
        item_checker.new_group = 'UGRC Shelf'

        #: Framework for setup to skip parts not testing
        item_checker.item.itemid = '0'
        item_checker.metatable_dict = {}

        checks.ItemChecker.setup(item_checker, 'foo')

        assert item_checker.new_folder == 'UGRC_Shelved'

    def test_setup_sets_shelved_flag(self, mocker):
        item_checker = mocker.Mock()
        item_checker.new_group = 'UGRC Shelf'

        #: Framework for setup to skip parts not testing
        item_checker.item.itemid = '0'
        item_checker.metatable_dict = {}

        checks.ItemChecker.setup(item_checker, 'foo')

        assert item_checker.static_shelved == 'shelved'


class TestMetadata:

    def test_metadata_check_sets_shelved_note(self, mocker):
        item_checker = mocker.Mock()
        # item_checker.arcpy_metadata = True
        item_checker.arcpy_metadata.xml = 'foo'
        item_checker.item.metadata = 'bar'
        item_checker.new_group = 'UGRC Shelf'
        item_checker.feature_class_path = 'baz'
        item_checker.results_dict = {}

        checks.ItemChecker.metadata_check(item_checker)

        assert item_checker.results_dict == {
            'metadata_fix': 'Y',
            'metadata_old': 'item.metadata from AGOL not shown due to length',
            'metadata_new': 'baz',
            'metadata_note': 'shelved'
        }


def test_lowercase_abbreviation_to_uppercase():
    test_tag = 'udot'
    cased = checks.tag_case(test_tag, Auditor.uppercased_tags, Auditor.articles)
    assert cased == 'UDOT'


def test_lowercased_tag_to_propercase():
    test_tag = 'random'
    cased = checks.tag_case(test_tag, Auditor.uppercased_tags, Auditor.articles)
    assert cased == 'Random'


def test_propercased_article_to_lowercase():
    test_tag = 'The'
    cased = checks.tag_case(test_tag, Auditor.uppercased_tags, Auditor.articles)
    assert cased == 'the'


def test_integrated_tag_check():
    test_tag = 'u.s. bureau Of Geoinformation'
    cased = checks.tag_case(test_tag, Auditor.uppercased_tags, Auditor.articles)
    assert cased == 'US Bureau of Geoinformation'


# def test_meta_tag_removal():
#     test_tag = 'Required: Common-Use Word Or Phrase Used To Describe the Subject of the Data Set'


def test_max_age_fixes_different_time(mocker):

    item = mocker.Mock()
    item.in_sgid = True
    item.properties = {'adminServiceInfo': {'cacheMaxAge': -1}}
    item.results_dict = {}

    checks.ItemChecker.cache_age_check(item, 5)

    assert item.results_dict == {'cache_age_fix': 'Y', 'cache_age_old': -1, 'cache_age_new': 5}


def test_max_age_doesnt_fix_same_time(mocker):

    item = mocker.Mock()
    item.in_sgid = True
    item.properties = {'adminServiceInfo': {'cacheMaxAge': 5}}
    item.results_dict = {}

    checks.ItemChecker.cache_age_check(item, 5)

    assert item.results_dict == {'cache_age_fix': 'N', 'cache_age_old': '', 'cache_age_new': ''}


def test_max_age_ignores_non_sgid_item(mocker):

    item = mocker.Mock()
    item.in_sgid = False
    item.results_dict = {}

    checks.ItemChecker.cache_age_check(item, 5)

    assert item.results_dict == {'cache_age_fix': 'N', 'cache_age_old': '', 'cache_age_new': ''}


def test_shelved_item_propercased_gets_shelved_thumbnail(mocker):

    item = mocker.Mock()
    item.new_group = 'UGRC Shelf'
    item.results_dict = {}

    thumbnail_dir = Path(__file__).parents[1] / 'thumbnails'

    checks.ItemChecker.thumbnail_check(item, thumbnail_dir)

    assert item.results_dict == {'thumbnail_fix': 'Y', 'thumbnail_path': str(thumbnail_dir / 'shelf.png')}


def test_same_group_doesnt_update_thumbnail(mocker):
    item = mocker.Mock()
    item.new_group = None
    item.results_dict = {}

    thumbnail_dir = Path(__file__).parents[1] / 'thumbnails'

    checks.ItemChecker.thumbnail_check(item, thumbnail_dir)

    assert item.results_dict == {'thumbnail_fix': 'N', 'thumbnail_path': ''}


def test_report_invalid_thumbnail_path(mocker):
    item = mocker.Mock()
    item.new_group = 'foo'
    item.results_dict = {}

    thumbnail_dir = Path(__file__).parents[1] / 'thumbnails'

    checks.ItemChecker.thumbnail_check(item, thumbnail_dir)

    assert item.results_dict == {
        'thumbnail_fix': 'N',
        'thumbnail_path': f'Thumbnail not found: {thumbnail_dir / "foo.png"}'
    }


def test_correct_thumbnails_dir(mocker):
    item = mocker.Mock()
    item.new_group = 'UGRC Shelf'
    item.results_dict = {}

    repo_path = Path(__file__).parents[1]
    thumbnail_path = repo_path / 'thumbnails'

    checks.ItemChecker.thumbnail_check(item, thumbnail_path)

    assert item.results_dict == {'thumbnail_fix': 'Y', 'thumbnail_path': str(thumbnail_path / 'shelf.png')}


def test_deprecated_added_to_existing_title(mocker):
    item_checker = mocker.Mock()
    item_checker.authoritative = 'deprecated'
    item_checker.title_from_metatable = 'foo'
    item_checker.item.title = 'foo'
    item_checker.results_dict = {}

    checks.ItemChecker.title_check(item_checker)

    assert item_checker.results_dict == {'title_fix': 'Y', 'title_old': 'foo', 'title_new': '{Deprecated} foo'}


def test_deprecated_added_to_new_title(mocker):
    item_checker = mocker.Mock()
    item_checker.authoritative = 'deprecated'
    item_checker.title_from_metatable = 'new'
    item_checker.item.title = 'current'
    item_checker.results_dict = {}

    checks.ItemChecker.title_check(item_checker)

    assert item_checker.results_dict == {'title_fix': 'Y', 'title_old': 'current', 'title_new': '{Deprecated} new'}


def test_title_updated(mocker):
    item_checker = mocker.Mock()
    item_checker.title_from_metatable = 'new'
    item_checker.item.title = 'current'
    item_checker.results_dict = {}

    checks.ItemChecker.title_check(item_checker)

    assert item_checker.results_dict == {'title_fix': 'Y', 'title_old': 'current', 'title_new': 'new'}


def test_old_title_retained(mocker):
    item_checker = mocker.Mock()
    item_checker.title_from_metatable = 'current'
    item_checker.item.title = 'current'
    item_checker.results_dict = {}

    checks.ItemChecker.title_check(item_checker)

    assert item_checker.results_dict == {'title_fix': 'N', 'title_old': 'current', 'title_new': ''}


def test_deprecated_not_added_to_new_title_if_already_in_new_metadata_title(mocker):
    item_checker = mocker.Mock()
    item_checker.authoritative = 'deprecated'
    item_checker.title_from_metatable = 'new (Deprecated)'
    item_checker.item.title = 'current'
    item_checker.results_dict = {}

    checks.ItemChecker.title_check(item_checker)

    assert item_checker.results_dict == {'title_fix': 'Y', 'title_old': 'current', 'title_new': 'new (Deprecated)'}


def test_deprecated_not_added_to_existing_title_if_already_in_title(mocker):
    item_checker = mocker.Mock()
    item_checker.authoritative = 'deprecated'
    item_checker.title_from_metatable = 'current (Deprecated)'
    item_checker.item.title = 'current (Deprecated)'
    item_checker.results_dict = {}

    checks.ItemChecker.title_check(item_checker)

    assert item_checker.results_dict == {'title_fix': 'N', 'title_old': 'current (Deprecated)', 'title_new': ''}


def test_deprecated_not_added_to_existing_title_if_already_prefixes_title(mocker):
    item_checker = mocker.Mock()
    item_checker.authoritative = 'deprecated'
    item_checker.title_from_metatable = 'current'
    item_checker.item.title = '{Deprecated} current'
    item_checker.results_dict = {}

    checks.ItemChecker.title_check(item_checker)

    assert item_checker.results_dict == {'title_fix': 'N', 'title_old': '{Deprecated} current', 'title_new': ''}
