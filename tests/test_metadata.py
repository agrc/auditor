class TestComments:

    def test_markdown_data_removes_md_comment(self, mocker):

        value = "fd67267e14534f3a96f1b53be22c0caf\n\n<!--- This layer does not have a row in the SGID Index. Is that intentional? --->"
