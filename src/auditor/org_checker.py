"""
Holds an OrgChecker object that runs checks at the organization level (instead of at the item level)
"""


class OrgChecker:
    """
    An OrgChecker runs checks at the org level, as opposed to the item level. For example, checking whether there are
    any items with the same title.

    To use, instantiate and then call run_checks(), which will run all checks.
    """

    def __init__(self, item_list):
        self.item_list = item_list

    def run_checks(self):
        """
        Run all checks in the OrgChecker. Any new checks should be added to this method.
        """

        self.check_for_duplicate_titles()

    def check_for_duplicate_titles(self):
        """
        Report any items in self.item_list that have duplicate titles.

        Returns: Dictionary of item ids for each duplicate title: {duplicate_title: [itemid, itemid, ...]}
        """
        seen_titles = {}
        duplicates = {}
        for item in self.item_list:
            if item.title in seen_titles:
                seen_titles[item.title].append(item.itemid)
            else:
                seen_titles[item.title] = [item.itemid]

        for title in seen_titles:
            if len(seen_titles[title]) > 1:
                duplicates[title] = seen_titles[title]

        return duplicates
