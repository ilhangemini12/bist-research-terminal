from bist_terminal.discovery.engine import DiscoveryEngine

class SPK:
    def broker_list(self): return [{'name':'A'}]
    def bank_list(self): return [{'name':'B'}]
class TSPB:
    def discover_workbook_url(self): return 'https://example/member.xlsx'
    def members(self,url): return [{'name':'A','_sheet':'Members'}]

def test_discovery_combines_official_registries():
    d=DiscoveryEngine(spk=SPK(),tspb=TSPB()).official_institutions()
    assert d['sources']['spk_brokers']['count']==1
    assert d['sources']['tspb_members']['count']==1
    assert d['sources']['tspb_members']['workbook_url'].endswith('member.xlsx')

class BadSPK(SPK):
    def broker_list(self): raise RuntimeError('down')

def test_discovery_isolates_registry_failure():
    d=DiscoveryEngine(spk=BadSPK(),tspb=TSPB()).official_institutions()
    assert d['sources']['spk_brokers']['status']=='DEGRADED'
    assert d['sources']['spk_banks']['status']=='ACTIVE'
    assert d['sources']['tspb_members']['status']=='ACTIVE'
