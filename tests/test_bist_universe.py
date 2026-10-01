from pathlib import Path
import json

from bist_terminal.providers.bist_universe import BistIndexUniverseProvider, enabled_indices

CSV = """BILESEN KODU;BULTEN_ADI;ENDEKS KODU;ENDEKS ADI\nTHYAO.E;TURK HAVA YOLLARI;XU030;BIST 30\nTHYAO.E;TURK HAVA YOLLARI;XU100;BIST 100\nAKBNK.E;AKBANK;XU030;BIST 30\nBAD HEADER;English;INDEX CODE;English\n"""

class Resp:
    def __init__(self, status=200, text=CSV, headers=None):
        self.status_code=status; self.text=text; self.headers=headers or {}
    def raise_for_status(self):
        if self.status_code >= 400: raise RuntimeError(self.status_code)

class Session:
    def __init__(self, responses): self.responses=list(responses); self.calls=[]
    def get(self, url, timeout, headers): self.calls.append(headers); return self.responses.pop(0)

def test_official_csv_parsing_and_union(tmp_path):
    p=BistIndexUniverseProvider(Session([Resp(headers={'ETag':'abc'})]),cache_dir=tmp_path)
    snap=p.get_components(['XU030','XU100'])
    assert snap.tickers == ['AKBNK','THYAO']
    assert len(snap.members['XU030']) == 2
    assert (tmp_path/'hisse_endeks_ds.csv').exists()

def test_conditional_get_uses_cache_on_304(tmp_path):
    (tmp_path/'hisse_endeks_ds.csv').write_text(CSV,encoding='utf-8')
    (tmp_path/'http_meta.json').write_text(json.dumps({'etag':'abc','last_modified':'Wed, 01 Oct 2026 00:00:00 GMT'}),encoding='utf-8')
    s=Session([Resp(status=304,text='')]); p=BistIndexUniverseProvider(s,cache_dir=tmp_path)
    snap=p.get_components(['XU030'])
    assert snap.cache_used and snap.not_modified
    assert s.calls[0]['If-None-Match']=='abc'

def test_blocked_network_falls_back_to_cache(tmp_path):
    (tmp_path/'hisse_endeks_ds.csv').write_text(CSV,encoding='utf-8')
    p=BistIndexUniverseProvider(Session([Resp(status=403)]),cache_dir=tmp_path)
    snap=p.get_components(['XU100'])
    assert snap.cache_used and snap.tickers == ['THYAO']

def test_enabled_indices_are_config_driven(tmp_path):
    c=tmp_path/'indices.yaml'; c.write_text('indices:\n  XU030: {enabled: true}\n  XTEST: {enabled: false}\n',encoding='utf-8')
    assert enabled_indices(c)==['XU030']
