from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Iterable
import json

import pandas as pd
import requests
import yaml

from bist_terminal.providers.base import Blocked, RateLimited, SchemaChanged

INDEX_COMPONENTS_URL = "https://www.borsaistanbul.com/datum/hisse_endeks_ds.csv"
REQUIRED_COLUMNS = {"BILESEN KODU", "BULTEN_ADI", "ENDEKS KODU", "ENDEKS ADI"}


@dataclass
class UniverseSnapshot:
    members: dict[str, list[dict[str, str]]]
    source_url: str = INDEX_COMPONENTS_URL
    cache_used: bool = False
    not_modified: bool = False

    @property
    def tickers(self) -> list[str]:
        return sorted({row["symbol"] for rows in self.members.values() for row in rows})


class BistIndexUniverseProvider:
    """Official Borsa Istanbul index-membership provider.

    The endpoint is reference/index-composition data, not a free real-time price feed.
    HTTP validators are persisted so scheduled jobs can use conditional GETs.
    """

    provider_id = "bist_index_components"
    upstream_vendor = "Borsa Istanbul"

    def __init__(self, session=None, timeout: int = 30, cache_dir: str | Path = "data/cache/bist_universe"):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.cache_dir = Path(cache_dir)
        self.csv_cache = self.cache_dir / "hisse_endeks_ds.csv"
        self.meta_cache = self.cache_dir / "http_meta.json"

    @staticmethod
    def _clean_symbol(value: object) -> str:
        return str(value or "").strip().upper().removesuffix(".E")

    @staticmethod
    def _clean_index(value: object) -> str:
        return str(value or "").strip().upper()

    def _parse(self, text: str) -> pd.DataFrame:
        try:
            df = pd.read_csv(StringIO(text), sep=";", dtype=str)
        except Exception as exc:
            raise SchemaChanged(f"BIST index CSV parse failed: {exc}") from exc
        if not REQUIRED_COLUMNS.issubset(df.columns):
            missing = sorted(REQUIRED_COLUMNS - set(df.columns))
            raise SchemaChanged(f"BIST index CSV missing columns: {missing}")
        # The feed has historically carried a duplicated English/header-like row.
        df = df.copy()
        df["symbol"] = df["BILESEN KODU"].map(self._clean_symbol)
        df["index_code"] = df["ENDEKS KODU"].map(self._clean_index)
        df["name"] = df["BULTEN_ADI"].fillna("").astype(str).str.strip()
        df["index_name"] = df["ENDEKS ADI"].fillna("").astype(str).str.strip()
        df = df[df["symbol"].str.match(r"^[A-Z0-9]{2,10}$", na=False)]
        df = df[df["index_code"].str.match(r"^X[A-Z0-9]{2,10}$", na=False)]
        if df.empty:
            raise SchemaChanged("BIST index CSV parsed but no valid memberships remained")
        return df[["symbol", "name", "index_code", "index_name"]].drop_duplicates()

    def _load_meta(self) -> dict:
        if not self.meta_cache.exists():
            return {}
        try:
            return json.loads(self.meta_cache.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write_cache(self, text: str, response) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.csv_cache.write_text(text, encoding="utf-8")
        meta = {
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "source_url": INDEX_COMPONENTS_URL,
        }
        self.meta_cache.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def fetch_dataframe(self) -> tuple[pd.DataFrame, bool, bool]:
        meta = self._load_meta()
        headers = {"User-Agent": "bist-research-terminal/0.3 (+personal research; conditional GET)"}
        if meta.get("etag"):
            headers["If-None-Match"] = meta["etag"]
        if meta.get("last_modified"):
            headers["If-Modified-Since"] = meta["last_modified"]
        try:
            r = self.session.get(INDEX_COMPONENTS_URL, timeout=self.timeout, headers=headers)
            if r.status_code == 304:
                if not self.csv_cache.exists():
                    raise SchemaChanged("304 returned but no local BIST universe cache exists")
                return self._parse(self.csv_cache.read_text(encoding="utf-8")), True, True
            if r.status_code == 429:
                raise RateLimited("BIST universe endpoint returned 429")
            if r.status_code in (401, 403):
                raise Blocked(f"BIST universe endpoint returned {r.status_code}")
            r.raise_for_status()
            df = self._parse(r.text)
            self._write_cache(r.text, r)
            return df, False, False
        except (Blocked, RateLimited, SchemaChanged):
            if self.csv_cache.exists():
                return self._parse(self.csv_cache.read_text(encoding="utf-8")), True, False
            raise
        except requests.RequestException:
            if self.csv_cache.exists():
                return self._parse(self.csv_cache.read_text(encoding="utf-8")), True, False
            raise

    def get_components(self, index_codes: Iterable[str]) -> UniverseSnapshot:
        wanted = {self._clean_index(x) for x in index_codes}
        df, cache_used, not_modified = self.fetch_dataframe()
        out: dict[str, list[dict[str, str]]] = {}
        for code in sorted(wanted):
            part = df[df["index_code"] == code]
            out[code] = part[["symbol", "name"]].to_dict("records")
        return UniverseSnapshot(out, cache_used=cache_used, not_modified=not_modified)


def enabled_indices(config_path: str | Path = "config/indices.yaml") -> list[str]:
    raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    items = raw.get("indices", {})
    return [str(code).upper() for code, cfg in items.items() if (cfg or {}).get("enabled", True)]
