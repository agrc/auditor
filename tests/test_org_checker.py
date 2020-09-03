from collections import namedtuple

from auditor.org_checker import OrgChecker


def test_duplicate_item_titles_added_to_dict(mocker):
    agol_item = namedtuple('agol_item', ['title', 'itemid'])
    item_list = [agol_item('foo', 1), agol_item('bar', 2), agol_item('foo', 3)]

    dupe_checker = OrgChecker(item_list)
    dupes = dupe_checker.check_for_duplicate_titles()

    assert dupes == {'foo': [1, 3]}


def test_duplicate_checker_called_once(mocker):

    mocker.patch('auditor.org_checker.OrgChecker.check_for_duplicate_titles')
    dupe_checker = OrgChecker(['empty list'])
    dupe_checker.run_checks()
    OrgChecker.check_for_duplicate_titles.assert_called_once()
