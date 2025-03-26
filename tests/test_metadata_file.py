import pytest

from auditor.metadata import MetadataFile


@pytest.fixture
def raw_markdown_from_github():
    return '# Title\n\nUtah Google Flight Blocks\n\n## ID\n\nfd67267e14534f3a96f1b53be22c0caf\n\n<!--- This layer does not have a row in the SGID Index. Is that intentional? --->\n\n## Brief Summary\n\nPolygon dataset of Google Imagery Service boundaries and associated flight dates from 2011-2018.\n\n## Summary\n\nThis dataset contains polygons representing project areas and completion dates for Google aerial imagery services from 2011-2018. This dataset shows project boundary information only and does not include the imagery itself.\n\n## Description\n\n### What is the dataset?\n\nAerial and satellite imagery is a powerful tool that can be used in data modeling, analysis, and cartography. This dataset shows areas in Utah where imagery has been collected, processed, and made available to the public through the Google imagery service.\n\n### What is the purpose of the dataset?\n\nThis dataset displays geographic areas of Utah where users can find aerial imagery coverage. This dataset is suitable as a reference for past imagery projects in Utah.\n\n### What does the dataset represent?\n\nThis dataset displays areas of imagery coverage as polygons. Each polygon represents a project area and includes the resolution, tile name, date of completion, square mileage, and year. These polygons do not include the mapped imagery themselves.\n\n### How was the dataset created?\n\nThis dataset was provided to UGRC from Google. It was created by dissolving individual flight lines into blocks with the same flight date.\n\n### How reliable and accurate is the dataset?\n\nThis dataset represents Google imagery service areas and dates for the years 2011-2018 only. Please reach out to [our team](https://gis.utah.gov/about/) with questions or concerns about this layer.\n\n## Credits\n\n### Data Source\n\nUGRC\n\n### Host\n\nUGRC\n\n## Restrictions\n\n## License\n\n## Tags\n\n- Remote sensing\n- Aerial imagery\n\n## Secondary Category\n\n## Data Page Link\n\n## Update\n\n### Update Schedule\n\nStatic\n\n### Previous Updates\n'


class TestMetadataFileSplitting:

    def test_split_markdown_to_sections_splits_on_newline(self, mocker):
        test_string = "# Title\n\nTest\n\n## ID\n\n1234abcd\n\n## Description\n\nTest\n\n## Credits\n\nTest\n\n## Tags\n\n- Test\n\n## Update\n\n### Update Schedule\n\nTest\n\n### Previous Updates\n\nTest"

        expected = {
            'Title': 'Test',
            'ID': '1234abcd',
            'Description': 'Test',
            'Credits': 'Test',
            'Tags': '- Test',
            'Update': "",
            'Update Schedule': 'Test',
            'Previous Updates': 'Test'

        }

        metadata_file_mock = mocker.patch("auditor.metadata.MetadataFile")
        metadata_file_mock.content = test_string
        metadata_file_mock._split_content = {}
        MetadataFile.split_markdown_to_sections(metadata_file_mock)

        assert metadata_file_mock._split_content == expected

class TestCommentRemoval:

    def test_remove_comments_removes_comment_at_beginning(self):
        test_string = "<!-- This is a comment -->Test"

        expected = "Test"

        output = MetadataFile._remove_comments_from_markdown(test_string)

        assert output == expected

    def test_remove_comments_removes_comment_at_end(self):
        test_string = "Test<!-- This is a comment -->"

        expected = "Test"

        output = MetadataFile._remove_comments_from_markdown(test_string)

        assert output == expected

    def test_remove_comments_removes_comment_in_middle(self):
        test_string = "Test<!-- This is a comment -->Test"

        expected = "TestTest"

        output = MetadataFile._remove_comments_from_markdown(test_string)

        assert output == expected

    def test_remove_comments_removes_multiple_comments(self):
        test_string = "Test<!-- This is a comment -->Test<!-- This is another comment -->Test"

        expected = "TestTestTest"

        output = MetadataFile._remove_comments_from_markdown(test_string)

        assert output == expected
