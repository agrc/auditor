# import arcgis

from validator import credentials
from validator import checks
from validator.validate import Validator

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
    cased = checks.tag_case(test_tag, Validator.uppercased_tags, Validator.articles)
    assert cased == 'UDOT'

def test_meta_tag_removal():
    test_tag = 'Required: Common-Use Word Or Phrase Used To Describe the Subject of the Data Set'
    