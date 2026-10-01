from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import re
import unicodedata
import zipfile

import pandas as pd
import requests

HOME = "https://www.kap.org.tr/tr"
DOWNLOAD = "https://www.kap.org.tr/tr/api/financialTable/download/{year}/{period}"
PERIOD_NAMES = {"1": "3M", "2": "6M", "3": "9M", "4": "FY"}
DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(20\d{2})")


def _clean(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _fold(value) -> str:
    text = _clean(value).upper().replace("İ", "I")
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def parse_tr_number(value) -> float | None:
    s = _clean(value)
    if not s or s in {"-", "—"}:
        return None
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1]
    s = s.replace(" ", "")
    if not re.fullmatch(r"-?[\d.,]+", s):
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        parts = s.lstrip("-").split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            s = s.replace(".", "")
    try:
        out = float(s)
    except ValueError:
        return None
    return -out if negative and out > 0 else out


def presentation_scale(label: str) -> tuple[str, float]:
    f = _fold(label)
    if "1.000.000" in f:
        return "TRY", 1_000_000.0
    if "1.000" in f:
        return "TRY", 1_000.0
    if "TL" in f:
        return "TRY", 1.0
    return "UNKNOWN", 1.0


def _period_end(label: str) -> str | None:
    dates = DATE_RE.findall(_clean(label))
    if not dates:
        return None
    dd, mm, yyyy = dates[-1]
    return f"{yyyy}-{mm}-{dd}"


def _period_columns(df: pd.DataFrame):
    if df.empty or df.shape[1] < 4:
        return None
    row0 = [_clean(x) for x in df.iloc[0].tolist()]
    row1 = [_clean(x) for x in df.iloc[1].tolist()] if len(df) > 1 else [""] * len(row0)
    current = [i for i, v in enumerate(row0) if "CARI DONEM" in _fold(v)]
    previous = [i for i, v in enumerate(row0) if "ONCEKI DONEM" in _fold(v)]
    if not current:
        return None

    def choose(cols):
        if not cols:
            return None
        totals = [i for i in cols if _fold(row1[i]) == "TOPLAM"]
        return totals[-1] if totals else cols[-1]

    cur = choose(current)
    prev = choose(previous)
    return {
        "current_col": cur,
        "previous_col": prev,
        "current_period": _period_end(row0[cur]) if cur is not None else None,
        "previous_period": _period_end(row0[prev]) if prev is not None else None,
    }


BALANCE = {
    "assets": ("TOPLAM VARLIKLAR", "AKTIF TOPLAMI", "VARLIKLAR TOPLAMI"),
    "equity": ("TOPLAM OZKAYNAKLAR", "OZKAYNAKLAR TOPLAMI"),
    "current_assets": ("DONEN VARLIKLAR", "TOPLAM DONEN VARLIKLAR"),
    "current_liabilities": ("KISA VADELI YUKUMLULUKLER", "TOPLAM KISA VADELI YUKUMLULUKLER"),
    "cash": ("NAKIT VE NAKIT BENZERLERI",),
    "inventories": ("STOKLAR",),
}
INCOME = {
    "revenue": ("HASILAT", "SATIS GELIRLERI"),
    "gross_profit": ("BRUT KAR (ZARAR)", "BRUT KAR"),
    "operating_profit": ("ESAS FAALIYET KARI (ZARARI)", "ESAS FAALIYET KARI"),
    "net_income": (
        "DONEM KARI (ZARARI)",
        "NET DONEM KARI (ZARARI)",
        "NET DONEM KARI VEYA ZARARI",
    ),
}
CASHFLOW = {
    "cash_from_operations": (
        "ISLETME FAALIYETLERINDEN NAKIT AKISLARI",
        "A. ISLETME FAALIYETLERINDEN ELDE EDILEN NAKIT AKISLARI",
    ),
}


def _classify(df: pd.DataFrame) -> dict[str, tuple[str, ...]] | None:
    if len(df) < 10:
        return None
    sample = " ".join(_fold(x) for x in df.iloc[:20].astype(str).to_numpy().ravel())
    if "NAKIT AKIS" in sample:
        return CASHFLOW
    if "KAR VEYA ZARAR" in sample or "GELIR TABLOSU" in sample:
        return INCOME
    if "FINANSAL DURUM" in sample or "BILANCO" in sample:
        return BALANCE
    return None


def _label(row) -> str:
    vals = [_clean(x) for x in row]
    if len(vals) > 1 and vals[1]:
        return vals[1]
    return vals[0] if vals else ""


def _match_metric(label: str, mapping: dict[str, tuple[str, ...]]) -> str | None:
    f = _fold(label)
    for metric, aliases in mapping.items():
        if any(f == _fold(alias) for alias in aliases):
            return metric
    return None


def parse_html_xls(payload: bytes, source_file: str | None = None) -> dict:
    tables = pd.read_html(BytesIO(payload), header=None)
    if not tables:
        raise ValueError("KAP workbook contains no HTML tables")

    currency = "UNKNOWN"
    scale = 1.0
    scope = "UNKNOWN"
    if tables[0].shape[1] >= 2:
        for _, row in tables[0].iterrows():
            key = _fold(row.iloc[0])
            val = _clean(row.iloc[1])
            if key == "SUNUM PARA BIRIMI":
                currency, scale = presentation_scale(val)
            elif key == "FINANSAL TABLO NITELIGI":
                scope = val or "UNKNOWN"

    facts: dict[str, float] = {}
    previous_facts: dict[str, float] = {}
    current_period = None
    previous_period = None
    matched_tables = 0

    for df in tables:
        mapping = _classify(df)
        if mapping is None:
            continue
        cols = _period_columns(df)
        if not cols or cols["current_col"] is None:
            continue
        matched_tables += 1
        current_period = current_period or cols["current_period"]
        previous_period = previous_period or cols["previous_period"]
        cur = cols["current_col"]
        prev = cols["previous_col"]
        for _, row in df.iterrows():
            vals = row.tolist()
            metric = _match_metric(_label(vals), mapping)
            if not metric or cur >= len(vals):
                continue
            value = parse_tr_number(vals[cur])
            if value is not None and metric not in facts:
                facts[metric] = value * scale
            if prev is not None and prev < len(vals):
                old = parse_tr_number(vals[prev])
                if old is not None and metric not in previous_facts:
                    previous_facts[metric] = old * scale

    core = ["assets", "equity", "net_income"]
    core_count = sum(k in facts for k in core)
    quality = min(100, 20 + matched_tables * 10 + core_count * 15 + (10 if current_period else 0))
    status = "PARSED_HIGH_CONFIDENCE" if quality >= 85 and core_count == 3 else (
        "PARSED_REVIEW_REQUIRED" if facts else "UNPARSEABLE"
    )
    return {
        "status": status,
        "quality_score": quality,
        "currency": currency,
        "scale": scale,
        "statement_scope": scope,
        "current_period": current_period,
        "previous_period": previous_period,
        "facts": facts,
        "previous_facts": previous_facts,
        "source_file": source_file,
        "matched_statement_tables": matched_tables,
    }


@dataclass
class KapArchive:
    year: int
    period: str
    source_url: str
    raw: bytes

    def __post_init__(self):
        self.zip = zipfile.ZipFile(BytesIO(self.raw))
        self.names = [i.filename for i in self.zip.infolist() if not i.is_dir()]

    def entry_for_ticker(self, ticker: str) -> str | None:
        symbol = ticker.replace(".IS", "").upper()
        pattern = re.compile(rf"(?:^|-){re.escape(symbol)}_(\d+)_{self.year}_{re.escape(self.period)}\.xls$", re.I)
        hits = []
        for name in self.names:
            m = pattern.search(name.rsplit("/", 1)[-1])
            if m:
                hits.append((int(m.group(1)), name))
        return max(hits)[1] if hits else None

    def parse_ticker(self, ticker: str) -> dict | None:
        name = self.entry_for_ticker(ticker)
        if not name:
            return None
        out = parse_html_xls(self.zip.read(name), source_file=name)
        out.update({"ticker": ticker.replace(".IS", "").upper(), "archive_year": self.year, "archive_period": self.period})
        return out


class KapBulkFinancialProvider:
    provider_id = "kap_bulk_financials"
    upstream_vendor = "KAP / MKK"

    def __init__(self, session=None, timeout: int = 90, max_bytes: int = 120_000_000):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.max_bytes = max_bytes

    def download_archive(self, year: int, period: str | int) -> KapArchive:
        period = str(period)
        if period not in PERIOD_NAMES:
            raise ValueError("period must be one of 1,2,3,4")
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; BIST-Research-Terminal/1.0; personal research)",
            "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        }
        self.session.get(HOME, timeout=30, headers=headers).raise_for_status()
        url = DOWNLOAD.format(year=int(year), period=period)
        api_headers = {**headers, "Accept": "*/*", "Referer": HOME, "Origin": "https://www.kap.org.tr"}
        with self.session.get(url, timeout=self.timeout, headers=api_headers, stream=True) as r:
            r.raise_for_status()
            buf = bytearray()
            for chunk in r.iter_content(1024 * 1024):
                if not chunk:
                    continue
                buf.extend(chunk)
                if len(buf) > self.max_bytes:
                    raise RuntimeError("KAP archive exceeded bounded byte limit")
        raw = bytes(buf)
        if not raw.startswith(b"PK"):
            raise RuntimeError("KAP financial download is not a ZIP archive")
        return KapArchive(int(year), period, url, raw)
