from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from io import StringIO
import re

from bs4 import BeautifulSoup
import requests

URL="https://gedik.com/analiz/model-portfoy/hisse-model-portfoy"
BROKER_ID="gedik_model_portfolio"
BROKER_NAME="Gedik Yatırım"

_TRY_RE=re.compile(r"[-+]?\d[\d.]*?(?:,\d+)?")
_DATE_RE=re.compile(r"\b(\d{2}\.\d{2}\.\d{4})\b")


def parse_tr_price(value: str | None) -> float | None:
    text=str(value or "").strip()
    m=_TRY_RE.search(text)
    if not m:
        return None
    s=m.group(0).replace(".","").replace(",",".")
    try:
        out=float(s)
    except ValueError:
        return None
    return out if out>0 else None


def _parse_date(value: str) -> str | None:
    try:
        return datetime.strptime(value,"%d.%m.%Y").date().isoformat()
    except ValueError:
        return None


def model_portfolio_date(text: str) -> str | None:
    """Return the latest date explicitly attached to a *stock* Model Portfolio item.

    Do not take the newest date on the whole page because the fund-model section can
    be updated more recently than the stock portfolio.
    """
    clean=re.sub(r"\s+"," ",str(text or "")).strip()
    candidates=[]
    patterns=[
        r"Model Portföy Güncellemesi[^\d]{0,220}(\d{2}\.\d{2}\.\d{4})",
        r"Model Portföy Güncelleme Raporu[^\d]{0,220}(\d{2}\.\d{2}\.\d{4})",
        r"Model Portföy Raporu[^\d]{0,220}(\d{2}\.\d{2}\.\d{4})",
    ]
    for pat in patterns:
        for raw in re.findall(pat,clean,flags=re.I):
            parsed=_parse_date(raw)
            if parsed:
                candidates.append(parsed)
    return max(candidates) if candidates else None


def parse_model_portfolio_html(html: str) -> dict:
    soup=BeautifulSoup(html,"html.parser")
    visible=soup.get_text(" ",strip=True)
    portfolio_date=model_portfolio_date(visible)

    target_table=None
    for table in soup.find_all("table"):
        header=" ".join(th.get_text(" ",strip=True) for th in table.find_all("th"))
        if "Hisse Kodu" in header and "Hedef Fiyat" in header:
            target_table=table
            break
        first=table.find("tr")
        first_text=first.get_text(" ",strip=True) if first else ""
        if "Hisse Kodu" in first_text and "Hedef Fiyat" in first_text:
            target_table=table
            break
    if target_table is None:
        raise RuntimeError("Gedik model-portfolio table schema unavailable")

    rows=[]
    trs=target_table.find_all("tr")
    if not trs:
        raise RuntimeError("Gedik model-portfolio table empty")
    header_cells=[c.get_text(" ",strip=True) for c in trs[0].find_all(["th","td"])]
    norm=[re.sub(r"\s+"," ",x).strip().casefold() for x in header_cells]

    def col(*needles):
        for i,name in enumerate(norm):
            if all(n.casefold() in name for n in needles):
                return i
        return None

    ticker_i=col("hisse","kodu")
    target_i=col("hedef","fiyat")
    company_i=col("şirket","adı")
    if ticker_i is None or target_i is None:
        raise RuntimeError("Gedik required model-portfolio columns missing")

    seen=set()
    for tr in trs[1:]:
        cells=[c.get_text(" ",strip=True) for c in tr.find_all(["th","td"])]
        if max(ticker_i,target_i)>=len(cells):
            continue
        ticker=re.sub(r"[^A-Z0-9]","",cells[ticker_i].upper())
        target=parse_tr_price(cells[target_i])
        if not ticker or not re.fullmatch(r"[A-Z0-9]{4,6}",ticker) or target is None:
            continue
        if ticker in seen:
            raise RuntimeError(f"duplicate Gedik ticker: {ticker}")
        seen.add(ticker)
        rows.append({
            "broker_id":BROKER_ID,
            "broker_name":BROKER_NAME,
            "ticker":ticker,
            "company_name":cells[company_i] if company_i is not None and company_i<len(cells) else None,
            "target_price":target,
            "model_portfolio_active":True,
            "portfolio_date":portfolio_date,
            "source_url":URL,
        })
    if not rows:
        raise RuntimeError("Gedik model-portfolio parser produced zero rows")
    return {
        "broker_id":BROKER_ID,
        "broker_name":BROKER_NAME,
        "portfolio_date":portfolio_date,
        "source_url":URL,
        "rows":rows,
    }


@dataclass
class GedikModelPortfolioProvider:
    session: requests.Session | None=None
    timeout: int=30

    def __post_init__(self):
        if self.session is None:
            self.session=requests.Session()
        self.headers={"User-Agent":"BIST-Research-Terminal/1.0 public-research-facts"}

    def fetch(self) -> dict:
        r=self.session.get(URL,headers=self.headers,timeout=self.timeout)
        r.raise_for_status()
        out=parse_model_portfolio_html(r.text)
        if not out.get("portfolio_date"):
            raise RuntimeError("Gedik stock-model portfolio update date unavailable")
        return out
