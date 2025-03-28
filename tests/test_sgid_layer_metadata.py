import pytest

from auditor.metadata import MetadataSchema


class TestMetadataSchema:

    def test_as_html_returns_correct_html(self, mocker):
        value1 = mocker.Mock()
        value1.as_html.return_value = "<p>Value 1</p>"
        value2 = mocker.Mock()
        value2.as_html.return_value = "<p>Value 2</p>"

        schema = MetadataSchema({"Field1": value1, "Field2": value2})

        expected_html = "<h3>Field1</h3><p>Value 1</p><h3>Field2</h3><p>Value 2</p>"

        assert schema.as_html() == expected_html
