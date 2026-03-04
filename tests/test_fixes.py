from auditor.fixes import ItemFixer


def test_cache_age_fix_runs_on_Y(mocker):

    update_def_mock = mocker.patch("arcgis.features.managers.FeatureLayerCollectionManager.update_definition")
    mocker.patch("arcgis.features.FeatureLayerCollection.fromitem")

    fixer_item = mocker.Mock()
    fixer_item.item_report = {"cache_age_fix": "Y", "cache_age_new": 5}

    ItemFixer.cache_age_fix(fixer_item)

    assert update_def_mock.called_called_once()


def test_cache_age_fix_doesnt_run_on_N(mocker):

    fixer_item = mocker.Mock()
    fixer_item.item_report = {"cache_age_fix": "N"}

    ItemFixer.cache_age_fix(fixer_item)

    assert fixer_item.item_report["cache_age_result"] == "No update needed for cacheMaxAge"


def test_cache_age_fix_sets_correct_results(mocker):

    mock_manager = mocker.Mock()
    mock_manager.update_definition.return_value = {"success": True}
    mock_flc = mocker.Mock()
    mock_flc.manager = mock_manager

    mocker.patch("arcgis.features.FeatureLayerCollection.fromitem", return_value=mock_flc)

    fixer_item = mocker.Mock()
    fixer_item.item_report = {"cache_age_fix": "Y", "cache_age_new": 5}

    ItemFixer.cache_age_fix(fixer_item)

    assert fixer_item.item_report["cache_age_result"] == "cacheMaxAge set to 5"


def test_cache_age_reports_failed_fix(mocker):

    mock_manager = mocker.Mock()
    mock_manager.update_definition.return_value = {"success": False}
    mock_flc = mocker.Mock()
    mock_flc.manager = mock_manager

    mocker.patch("arcgis.features.FeatureLayerCollection.fromitem", return_value=mock_flc)

    fixer_item = mocker.Mock()
    fixer_item.item_report = {"cache_age_fix": "Y", "cache_age_new": 5}

    ItemFixer.cache_age_fix(fixer_item)

    assert fixer_item.item_report["cache_age_result"] == "Failed to set cacheMaxAge to 5"


def test_folder_fix_no_update_on_N(mocker):

    fixer_item = mocker.Mock()
    fixer_item.item_report = {"folder_fix": "N"}

    ItemFixer.folder_fix(fixer_item)

    assert fixer_item.item_report["folder_result"] == "No update needed for folder"


def test_folder_fix_reports_folder_not_found(mocker):

    mock_gis = mocker.Mock()
    mock_gis.content.folders.get.return_value = None

    fixer_item = mocker.Mock()
    fixer_item.gis = mock_gis
    fixer_item.item_report = {"folder_fix": "Y", "folder_new": "Transportation"}

    ItemFixer.folder_fix(fixer_item)

    mock_gis.content.folders.get.assert_called_once_with("Transportation")
    assert fixer_item.item_report["folder_result"] == "'Transportation' folder not found"


def test_folder_fix_reports_failed_move(mocker):

    mock_folder = mocker.Mock()
    mock_gis = mocker.Mock()
    mock_gis.content.folders.get.return_value = mock_folder

    fixer_item = mocker.Mock()
    fixer_item.gis = mock_gis
    fixer_item.item.move.return_value = {"success": False}
    fixer_item.item_report = {"folder_fix": "Y", "folder_new": "Transportation"}

    ItemFixer.folder_fix(fixer_item)

    assert fixer_item.item_report["folder_result"] == "Failed to move item to 'Transportation' folder"


def test_folder_fix_moves_item_to_folder(mocker):

    mock_folder = mocker.Mock()
    mock_gis = mocker.Mock()
    mock_gis.content.folders.get.return_value = mock_folder

    fixer_item = mocker.Mock()
    fixer_item.gis = mock_gis
    fixer_item.item.move.return_value = {"success": True}
    fixer_item.item_report = {"folder_fix": "Y", "folder_new": "Transportation"}

    ItemFixer.folder_fix(fixer_item)

    fixer_item.item.move.assert_called_once_with(mock_folder)
    assert fixer_item.item_report["folder_result"] == "Item moved to 'Transportation' folder"
