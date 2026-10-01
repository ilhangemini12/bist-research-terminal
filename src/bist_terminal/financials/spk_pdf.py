from __future__ import annotations

import base64
from dataclasses import dataclass, asdict
from datetime import date
from io import BytesIO
import re
import unicodedata
from typing import Iterable

MONTHS_TR = {
    "OCAK": 1, "ŞUBAT": 2, "SUBAT": 2, "MART": 3, "NİSAN": 4, "NISAN": 4,
    "MAYIS": 5, "HAZİRAN": 6, "HAZIRAN": 6, "TEMMUZ": 7, "AĞUSTOS": 8, "AGUSTOS": 8,
    "EYLÜL": 9, "EYLUL": 9, "EKİM": 10, "EKIM": 10, "KASIM": 11, "ARALIK": 12,
}
DATE_RE = re.compile(
    r"(?P<day>\d{1,2})\s+(?P<month>Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|Haziran|Temmuz|Ağustos|Agustos|Eylül|Eylul|Ekim|Kasım|Kasim|Aralık|Aralik)\s+(?P<year>20\d{2})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedFact:
    metric: str
    period: str
    value: float | None
    page: int
    raw_label: str

    def as_dict(self):
        return asdict(self)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _fold(text: str) -> str:
    text = _clean(text).upper().replace("İ", "I").replace("İ", "I")
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def parse_tr_number(token: str) -> float | None:
    s = _clean(token)
    if not s or s == "-":
        return None
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1]
    s = s.replace(" ", "").replace(".", "").replace(",", ".")
    if s.endswith("%"):
        return None
    try:
        value = float(s)
    except ValueError:
        return None
    return -value if negative else value


def extract_periods(text: str) -> list[str]:
    periods = []
    for match in DATE_RE.finditer(text or ""):
        month = MONTHS_TR.get(_fold(match.group("month")))
        if month is None:
            continue
        iso = date(int(match.group("year")), month, int(match.group("day"))).isoformat()
        if iso not in periods:
            periods.append(iso)
    return periods


def _tail_values(line: str, count: int) -> list[float | None] | None:
    tokens = _clean(line).split()
    values: list[float | None] = []
    numericish = re.compile(r"^\(?-?\d[\d.,]*\)?$|^-$")
    for token in reversed(tokens):
        if numericish.match(token):
            values.append(parse_tr_number(token))
            if len(values) == count:
                return list(reversed(values))
    return None


def _first_page(page_texts: list[str], required_folded: Iterable[str], max_page: int = 20) -> int | None:
    required = list(required_folded)
    for idx, text in enumerate(page_texts[:max_page]):
        folded = _fold(text)
        if all(term in folded for term in required):
            return idx
    return None


def _periods_for_pages(page_texts: list[str], indices: list[int], min_periods: int = 2) -> list[str]:
    for idx in indices:
        if idx is None or idx < 0 or idx >= len(page_texts):
            continue
        periods = extract_periods(page_texts[idx])
        if len(periods) >= min_periods:
            return periods[:3]
    return []


BALANCE_METRICS = {
    "total_assets": ("TOPLAM VARLIKLAR",),
    "equity": ("TOPLAM OZKAYNAKLAR",),
    "total_sources": ("TOPLAM KAYNAKLAR",),
    "current_assets": ("TOPLAM DONEN VARLIKLAR",),
    "current_liabilities": ("TOPLAM KISA VADELI YUKUMLULUKLER",),
    "noncurrent_liabilities": ("TOPLAM UZUN VADELI YUKUMLULUKLER",),
    "cash": ("NAKIT VE NAKIT BENZERLERI",),
    "inventories": ("STOKLAR",),
}

INCOME_METRICS = {
    "revenue": ("HASILAT",),
    "gross_profit": ("BRUT KAR", "BRUT KAR (ZARAR)"),
    "operating_profit": ("ESAS FAALIYET KARI", "ESAS FAALIYET KARI (ZARARI)"),
    "pretax_income": ("SURDURULEN FAALIYETLER VERGI ONCESI DONEM KARI",),
    "net_income": ("NET DONEM KARI", "NET DONEM KARI (ZARARI)"),
}

CASHFLOW_METRICS = {
    "cash_from_operations": ("A. ISLETME FAALIYETLERINDEN ELDE EDILEN NAKIT AKISLARI",),
}


def _match_metric(line: str, mapping: dict[str, tuple[str, ...]]) -> tuple[str, str] | None:
    folded = _fold(line)
    for metric, labels in mapping.items():
        for label in labels:
            lf = _fold(label)
            if folded.startswith(lf):
                return metric, label
    return None


def _parse_page_group(page_texts: list[str], pages: list[int], periods: list[str], mapping: dict[str, tuple[str, ...]]) -> list[ParsedFact]:
    facts: list[ParsedFact] = []
    seen: set[tuple[str, str]] = set()
    if not periods:
        return facts
    for idx in pages:
        if idx is None or idx < 0 or idx >= len(page_texts):
            continue
        for raw in (page_texts[idx] or "").splitlines():
            line = _clean(raw)
            if not line:
                continue
            matched = _match_metric(line, mapping)
            if not matched:
                continue
            metric, _ = matched
            values = _tail_values(line, len(periods))
            if values is None:
                continue
            label = re.split(r"\s+\(?-?\d[\d.,]*\)?(?:\s|$)", line, maxsplit=1)[0].strip() or metric
            for period, value in zip(periods, values):
                key = (metric, period)
                if key in seen:
                    continue
                seen.add(key)
                facts.append(ParsedFact(metric, period, value, idx + 1, label))
    return facts


def parse_statement_pages(page_texts: list[str], metadata: dict | None = None) -> dict:
    if not page_texts:
        return {
            "status": "UNPARSEABLE",
            "quality_score": 0,
            "facts": [],
            "periods": [],
            "checks": {"reason": "no text pages"},
            "metadata": metadata or {},
        }

    balance_anchor = _first_page(page_texts, ["TOPLAM VARLIKLAR"])
    income_anchor = _first_page(page_texts, ["HASILAT", "NET DONEM KARI"])
    cash_anchor = _first_page(page_texts, ["ISLETME FAALIYETLERINDEN ELDE EDILEN NAKIT AKISLARI"])

    balance_pages = [] if balance_anchor is None else [balance_anchor, balance_anchor + 1]
    income_pages = [] if income_anchor is None else [income_anchor]
    cash_pages = [] if cash_anchor is None else [cash_anchor]

    balance_periods = _periods_for_pages(page_texts, balance_pages)
    income_periods = _periods_for_pages(page_texts, income_pages)
    cash_periods = _periods_for_pages(page_texts, cash_pages)

    facts = []
    facts += _parse_page_group(page_texts, balance_pages, balance_periods, BALANCE_METRICS)
    facts += _parse_page_group(page_texts, income_pages, income_periods, INCOME_METRICS)
    facts += _parse_page_group(page_texts, cash_pages, cash_periods, CASHFLOW_METRICS)

    by_period: dict[str, dict[str, float | None]] = {}
    for fact in facts:
        by_period.setdefault(fact.period, {})[fact.metric] = fact.value

    all_periods = []
    for seq in (balance_periods, income_periods, cash_periods):
        for p in seq:
            if p not in all_periods:
                all_periods.append(p)

    latest = all_periods[0] if all_periods else None
    latest_values = by_period.get(latest, {}) if latest else {}
    assets = latest_values.get("total_assets")
    sources = latest_values.get("total_sources")
    balance_ok = None
    if assets is not None and sources is not None:
        scale = max(abs(assets), abs(sources), 1.0)
        balance_ok = abs(assets - sources) / scale <= 1e-6

    core = ["total_assets", "equity", "revenue", "net_income"]
    core_count = sum(latest_values.get(k) is not None for k in core)
    score = 0
    score += 20 if balance_anchor is not None else 0
    score += 20 if income_anchor is not None else 0
    score += 10 if cash_anchor is not None else 0
    score += 20 if len(balance_periods) >= 2 and len(income_periods) >= 2 else 0
    score += 20 if core_count == len(core) else core_count * 5
    score += 10 if balance_ok is True else 0
    score = min(score, 100)

    status = "PARSED_HIGH_CONFIDENCE" if score >= 85 and balance_ok is True else (
        "PARSED_REVIEW_REQUIRED" if facts else "UNPARSEABLE"
    )
    return {
        "status": status,
        "quality_score": score,
        "periods": all_periods,
        "facts": [f.as_dict() for f in facts],
        "facts_by_period": by_period,
        "statement_pages": {
            "balance": [p + 1 for p in balance_pages if p < len(page_texts)],
            "income": [p + 1 for p in income_pages],
            "cashflow": [p + 1 for p in cash_pages],
        },
        "checks": {
            "balance_identity_ok": balance_ok,
            "latest_period": latest,
            "latest_core_fact_count": core_count,
        },
        "metadata": metadata or {},
    }


def parse_pdf_base64(file_data: str, metadata: dict | None = None) -> dict:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf dependency missing") from exc
    raw = base64.b64decode(file_data, validate=True)
    if not raw.startswith(b"%PDF"):
        raise ValueError("financial report payload is not a PDF")
    reader = PdfReader(BytesIO(raw))
    page_texts = [(page.extract_text() or "") for page in reader.pages]
    result = parse_statement_pages(page_texts, metadata=metadata)
    result["pdf_pages"] = len(page_texts)
    result["text_pages"] = sum(bool(_clean(x)) for x in page_texts)
    result["pdf_bytes"] = len(raw)
    return result
