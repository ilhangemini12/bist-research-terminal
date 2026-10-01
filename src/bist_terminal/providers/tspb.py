from __future__ import annotations

from io import BytesIO
from urllib.parse import urljoin
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

PAGE_URL = "https://tspb.org.tr/uye-bilgileri/"


class TSPBMembersProvider:
    """Public TSPB member-list discovery client.

    The detailed member workbook URL is discovered from the official member page on
    each monthly discovery run instead of hardcoding a dated upload path. This
    provider is registry/discovery-only; it is never used as a market-price feed.
    """

    provider_id = "tspb_members"

    def __init__(self, session=None, timeout: int = 20):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.headers = {"User-Agent": "bist-research-terminal/0.3 (+research; free-first)"}

    def discover_workbook_url(self) -> str:
        r = self.session.get(PAGE_URL, timeout=self.timeout, headers=self.headers)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        candidates=[]
        for a in soup.find_all("a", href=True):
            href=a.get("href", "").strip()
            text=" ".join(a.stripped_strings).lower()
            if href.lower().endswith((".xlsx", ".xls")):
                score=0
                if "üye" in text or "uye" in text: score += 5
                if "detay" in text: score += 3
                if "borsa üyesi" in text or "borsa uyesi" in text: score -= 2
                candidates.append((score,urljoin(PAGE_URL,href)))
        if not candidates:
            raise ValueError("TSPB detailed member workbook link not found")
        candidates.sort(key=lambda x:x[0], reverse=True)
        return candidates[0][1]

    def download_workbook(self, url: str | None = None) -> bytes:
        url=url or self.discover_workbook_url()
        r=self.session.get(url, timeout=self.timeout, headers=self.headers)
        r.raise_for_status()
        content=getattr(r,"content",b"")
        if not content or (not content.startswith(b"PK") and not content.startswith(bytes.fromhex("D0CF11E0"))):
            raise ValueError("TSPB member workbook payload is not an Excel file")
        return content

    def member_sheets(self, url: str | None = None) -> dict[str, pd.DataFrame]:
        raw=self.download_workbook(url)
        return pd.read_excel(BytesIO(raw), sheet_name=None)

    @staticmethod
    def _clean(v: Any):
        if pd.isna(v): return None
        if hasattr(v,"item"):
            try: return v.item()
            except Exception: pass
        return v

    def members(self, url: str | None = None) -> list[dict[str, Any]]:
        sheets=self.member_sheets(url)
        out=[]
        for sheet_name,df in sheets.items():
            if df is None or df.empty: continue
            df=df.dropna(how="all")
            for _,row in df.iterrows():
                rec={str(k).strip():self._clean(v) for k,v in row.to_dict().items() if str(k).strip()}
                if not any(v not in (None,"") for v in rec.values()): continue
                rec["_sheet"]=sheet_name
                out.append(rec)
        return out
