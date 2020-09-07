# import arcgis

import unittest

from collections import namedtuple

from auditor import credentials
from auditor import checks
from auditor.auditor import Auditor

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


def test_upercased_tags():
    test_tag = 'udot'
    cased = checks.tag_case(test_tag, Auditor.uppercased_tags, Auditor.articles)
    assert cased == 'UDOT'


# def test_meta_tag_removal():
#     test_tag = 'Required: Common-Use Word Or Phrase Used To Describe the Subject of the Data Set'


def test_max_age_fixes_different_time(mocker):

    item = mocker.Mock()
    item.in_sgid = True
    item.properties = {'adminServiceInfo' : {'cacheMaxAge': -1}}
    item.results_dict = {}

    checks.ItemChecker.cache_age_check(item, 5)

    assert item.results_dict == {'cache_age_fix': 'Y', 'cache_age_old': -1, 'cache_age_new': 5}


def test_max_age_doesnt_fix_same_time(mocker):

    item = mocker.Mock()
    item.in_sgid = True
    item.properties = {'adminServiceInfo' : {'cacheMaxAge': 5}}
    item.results_dict = {}

    checks.ItemChecker.cache_age_check(item, 5)

    assert item.results_dict == {'cache_age_fix': 'N', 'cache_age_old':'', 'cache_age_new':''}


def test_max_age_ignores_non_sgid_item(mocker):

    item = mocker.Mock()
    item.in_sgid = False
    item.results_dict = {}

    checks.ItemChecker.cache_age_check(item, 5)

    assert item.results_dict == {'cache_age_fix': 'N', 'cache_age_old': '', 'cache_age_new': ''}
