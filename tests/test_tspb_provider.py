from bist_terminal.providers.tspb import TSPBMembersProvider

class R:
    def __init__(self,text='',content=b''): self.text=text; self.content=content
    def raise_for_status(self): pass
class S:
    def __init__(self): self.calls=[]
    def get(self,url,**kwargs):
        self.calls.append(url)
        if url.endswith('/uye-bilgileri/'):
            return R('<a href="/files/old_stats.xlsx">Borsa Üyesi Sayısı</a><a href="/wp-content/member.xlsx">Detaylı Üye Listesi</a>')
        return R(content=b'PKfake')

def test_tspb_discovers_detailed_member_workbook_not_stats():
    p=TSPBMembersProvider(session=S())
    assert p.discover_workbook_url()=='https://tspb.org.tr/wp-content/member.xlsx'

def test_tspb_rejects_non_excel_payload():
    class Bad(S):
        def get(self,url,**kwargs): return R(text='x',content=b'<html>blocked</html>')
    p=TSPBMembersProvider(session=Bad())
    try:
        p.download_workbook('https://tspb.org.tr/a.xlsx')
        assert False
    except ValueError as e:
        assert 'not an Excel file' in str(e)
