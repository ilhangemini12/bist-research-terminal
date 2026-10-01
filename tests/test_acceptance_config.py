from pathlib import Path
import yaml

REQUIRED_PRESETS={
    'VALUE','QUALITY','GROWTH','DIVIDEND','MOMENTUM','OVERSOLD','TREND','LOW_DEBT','HIGH_ROIC','HIGH_FCF_YIELD',
    'VALUE_QUALITY','VALUE_RSI','GROWTH_MOMENTUM','OZKAN_FILIZ_SECTOR_VALUE','VOLKAN_KOCABAS_VALUE_GROWTH','VK_RSI_DIP_RECOVERY','VK_TREND_MOMENTUM'
}


def test_required_preset_library_present():
    data=yaml.safe_load(Path('config/presets.yaml').read_text())['presets']
    assert REQUIRED_PRESETS <= set(data)
    assert data['OZKAN_FILIZ_SECTOR_VALUE']['description']=='Public methodology reconstruction'
    assert data['VOLKAN_KOCABAS_VALUE_GROWTH']['description']=='Public examples reconstruction'
    assert 'Approximation' in data['VK_RSI_DIP_RECOVERY']['description']


def test_tinyfish_never_active_and_paid_sources_skipped():
    providers=yaml.safe_load(Path('config/source_catalog.yaml').read_text())['providers']
    tiny=next(x for x in providers if x['provider_id']=='tinyfish')
    assert tiny['status']=='PAID_SOURCE_SKIPPED'
    assert tiny['terms_status']=='USER_FORBIDDEN'
    for p in providers:
        if p.get('free') is False and p['provider_id']!='tinyfish':
            assert p['status'] in {'PAID_SOURCE_SKIPPED','DISABLED'}


def test_runtime_requires_two_lineages():
    cfg=yaml.safe_load(Path('config/runtime.yaml').read_text())
    assert cfg['price_verification']['minimum_independent_upstreams'] >= 2
    assert cfg['price_verification']['verified_status']=='VERIFIED_2X'
