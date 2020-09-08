from auditor.fixes import ItemFixer


def test_cache_age_fix_runs_on_Y(mocker):
    
    update_def_mock = mocker.patch('arcgis.features.managers.FeatureLayerCollectionManager.update_definition')
    mocker.patch('arcgis.features.FeatureLayerCollection.fromitem')

    fixer_item = mocker.Mock()
    fixer_item.item_report = {'cache_age_fix': 'Y', 'cache_age_new': 5}

    ItemFixer.cache_age_fix(fixer_item)

    assert update_def_mock.called_called_once()


def test_cache_age_fix_doesnt_run_on_N(mocker):

    fixer_item = mocker.Mock()
    fixer_item.item_report = {'cache_age_fix': 'N'}

    ItemFixer.cache_age_fix(fixer_item)

    assert fixer_item.item_report['cache_age_result'] == 'No update needed for cacheAgeMax'


def test_cache_age_fix_sets_correct_results(mocker):

    mock_manager = mocker.Mock()
    mock_manager.update_definition.return_value = {'success': True}
    mock_flc = mocker.Mock()
    mock_flc.manager = mock_manager

    mocker.patch('arcgis.features.FeatureLayerCollection.fromitem', return_value = mock_flc)

    fixer_item = mocker.Mock()
    fixer_item.item_report = {'cache_age_fix': 'Y', 'cache_age_new': 5}

    ItemFixer.cache_age_fix(fixer_item)

    assert fixer_item.item_report['cache_age_result'] == 'cacheAgeMax set to 5'


def test_cache_age_reports_failed_fix(mocker):

    mock_manager = mocker.Mock()
    mock_manager.update_definition.return_value = {'success': False}
    mock_flc = mocker.Mock()
    mock_flc.manager = mock_manager

    mocker.patch('arcgis.features.FeatureLayerCollection.fromitem', return_value = mock_flc)

    fixer_item = mocker.Mock()
    fixer_item.item_report = {'cache_age_fix': 'Y', 'cache_age_new': 5}

    ItemFixer.cache_age_fix(fixer_item)

    assert fixer_item.item_report['cache_age_result'] == 'Failed to set cacheAgeMax to 5'

