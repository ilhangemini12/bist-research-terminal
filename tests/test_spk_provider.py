from bist_terminal.providers.spk import SPKRegistryProvider


class FakeResponse:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): return None
    def json(self): return self.payload


class FakeSession:
    def __init__(self): self.calls = []
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse({"ok": True, "url": url, "params": kwargs.get("params")})


def test_spk_public_endpoint_paths_and_params():
    s = FakeSession(); p = SPKRegistryProvider(session=s)
    p.listed_companies()
    p.special_disclosures(companyCode=123, dateBegin="2026-09-01")
    p.financial_reports(companyCode=123)
    p.financial_report(123)
    urls = [x[0] for x in s.calls]
    assert urls[0].endswith('/HalkaAcikSirket/api/Sirketler/Borsa')
    assert urls[1].endswith('/CompanyData/api/OzelDurumAciklamalari')
    assert s.calls[1][1]['params']['companyCode'] == 123
    assert urls[2].endswith('/CompanyData/api/FinansalRaporlar')
    assert urls[3].endswith('/CompanyData/api/FinansalRapor/123')


def test_spk_activity_permission_pass_through():
    s = FakeSession(); p = SPKRegistryProvider(session=s)
    p.broker_activity_permissions(id=42, authType=1, certificateType=3)
    assert s.calls[-1][1]['params'] == {'id': 42, 'authType': 1, 'certificateType': 3}
