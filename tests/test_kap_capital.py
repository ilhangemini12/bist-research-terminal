from bist_terminal.providers.kap_capital import parse_company_mapping, parse_total_shares


def test_parse_company_mapping_from_escaped_next_state():
    raw=r'''<script>[\"x\",{\"mkkMemberOid\":\"OID1\",\"kapMemberTitle\":\"TURK HAVA\",\"relatedMemberTitle\":\"AUDIT\",\"stockCode\":\"THYAO\",\"cityName\":\"ISTANBUL\"},{\"mkkMemberOid\":\"OID2\",\"kapMemberTitle\":\"ALBARAKA\",\"stockCode\":\"ALBRK ALK\"}]</script>'''
    m=parse_company_mapping(raw)
    assert m["THYAO"]["mkk_member_oid"]=="OID1"
    assert m["ALBRK"]["mkk_member_oid"]=="OID2"


def test_parse_explicit_total_share_count():
    raw='''<table><thead><tr><th>Borsa Kodu</th><th>Toplam Pay Adedi</th></tr></thead>
    <tbody><tr><td>THYAO</td><td>1.380.000.000,00</td></tr></tbody></table>'''
    out=parse_total_shares(raw,"THYAO")
    assert out["method"]=="EXPLICIT_TOTAL_SHARE_COUNT"
    assert out["total_shares"]==1_380_000_000


def test_parse_share_group_nominal_ratio_without_one_tl_assumption():
    raw='''<table><thead><tr><th>Pay Grubu</th><th>Beher Payın Nominal Değeri (TL)</th><th>Payların Nominal Değeri</th></tr></thead>
    <tbody><tr><td>A</td><td>0,01</td><td>22.500.000</td></tr>
    <tr><td>B</td><td>0,01</td><td>1.477.500.000</td></tr></tbody></table>'''
    out=parse_total_shares(raw,"MARTI")
    assert out["method"]=="SHARE_GROUP_NOMINAL_RATIO"
    assert out["total_shares"]==150_000_000_000
