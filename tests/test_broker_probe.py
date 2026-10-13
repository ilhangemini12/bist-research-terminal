from types import SimpleNamespace
from scripts import probe_broker_public_models as probe


def test_probe_reports_dates_without_persisting_targets(monkeypatch):
    html = '<p>Model Portföy 13.10.2026</p><table><tr><th>HEDEF FİYAT</th></tr><tr><td>987654321</td></tr></table>'
    def get(url, **kwargs):
        text = 'User-agent: *\nAllow: /' if url.endswith('robots.txt') else html
        return SimpleNamespace(status_code=200,text=text,content=text.encode(),raise_for_status=lambda:None)
    monkeypatch.setattr(probe.requests, 'get', get)
    out = probe.probe({'id':'test', 'url':'https://example.com/portfolio'})
    assert out['dates_visible'] == ['13.10.2026']
    assert out['table_count'] == 1 and out['robots_can_fetch']
    assert '987654321' not in str(out)
