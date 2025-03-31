import pytest

from auditor.metadata import MetadataSchema, SGIDLayerMetadata


class TestMetadataSchema:
    def test_as_html_returns_correct_html(self, mocker):
        value1 = mocker.Mock()
        value1.as_html.return_value = "<p>Value 1</p>"
        value2 = mocker.Mock()
        value2.as_html.return_value = "<p>Value 2</p>"

        schema = MetadataSchema({"Field1": value1, "Field2": value2})

        expected_html = "<h3>Field1</h3><p>Value 1</p><h3>Field2</h3><p>Value 2</p>"

        assert schema.as_html() == expected_html


class TestDefaults:
    def test_restrictions_default(self):
        test_md = SGIDLayerMetadata()

        assert (
            test_md.restrictions
            == """
        The data, including but not limited to geographic data, tabular data, and analytical data, are provided “as is” and “as available”, with no guarantees relating to the availability, completeness, or accuracy of data, and without any express or implied warranties.

        These data are provided as a public service for informational purposes only. You are solely responsible for obtaining the proper evaluation of a location and associated data by a qualified professional. UGRC reserves the right to change, revise, suspend or discontinue published data and services without notice at any time.

        Neither UGRC nor the State of Utah are responsible for any misuse or misrepresentation of the data. UGRC and the State of Utah are not obligated to provide you with any maintenance or support. The user assumes the entire risk as to the quality and performance of the data. You agree to hold the State of Utah harmless for any claims, liability, costs, and damages relating to your use of the data. You agree that your sole remedy for any dissatisfaction or claims is to discontinue use of the data."""
        )

    def test_license_default(self):
        test_md = SGIDLayerMetadata()

        assert test_md.license_ == "CC BY 4.0"
