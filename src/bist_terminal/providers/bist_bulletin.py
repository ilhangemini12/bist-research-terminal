from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO, StringIO
import csv
import zipfile
import requests

from bist_terminal.models import PriceObservation
from bist_terminal.providers.base import BaseProvider, ProviderError, RateLimited, Blocked, SchemaChanged


class BistDailyBulletinProvider(BaseProvider):
    """Official Borsa Istanbul Equity Market end-of-day bulletin provider.

    The bulletin ZIP is fetched at most once per provider instance and parsed into
    an in-memory ticker map. This avoids one network request per constituent.
    Only raw EQT rows with ``*.E`` transaction codes are accepted.
    """

    provider_id = "bist_daily_bulletin"
    upstream_vendor = "Borsa Istanbul"
    base_url = "https://www.borsaistanbul.com"

    def __init__(self, trade_date: str, session=None, timeout: int = 30, suffix: str = "1"):
        self.trade_date = str(trade_date)
        self.session = session or requests.Session()
        self.timeout = timeout
        self.suffix = str(suffix)
        self._prices: dict[str, dict] | None = None
        self._source_url: str | None = None

    def _url(self) -> str:
        d = datetime.fromisoformat(self.trade_date).date()
        return f"{self.base_url}/data/thb/{d:%Y}/{d:%m}/thb{d:%Y%m%d}{self.suffix}.zip"

    @staticmethod
    def _decode(raw: bytes) -> str:
        for enc in ("utf-8-sig", "cp1254", "latin-1"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        raise SchemaChanged("unable to decode BIST bulletin")

    @staticmethod
    def _num(value: str | None) -> float | None:
        if value is None:
            return None
        s = str(value).strip().replace(" ", "")
        if not s:
            return None
        if "," in s and "." not in s:
            s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    def _fetch(self):
        url = self._url()

        def once():
            r = self.session.get(url, timeout=self.timeout, headers={"User-Agent": "BIST-Research-Terminal/1.0"})
            if r.status_code == 429:
                raise RateLimited("BIST bulletin HTTP 429")
            if r.status_code in (401, 403):
                raise Blocked(f"BIST bulletin HTTP {r.status_code}")
            if r.status_code == 404:
                raise ProviderError(f"BIST bulletin not published for {self.trade_date}")
            r.raise_for_status()
            if not r.content.startswith(b"PK"):
                raise SchemaChanged("BIST bulletin response is not a ZIP archive")
            return r

        r = self.with_retry(once)
        self._source_url = url
        try:
            with zipfile.ZipFile(BytesIO(r.content)) as zf:
                names = [n for n in zf.namelist() if n.lower().endswith((".csv", ".txt"))]
                if not names:
                    raise SchemaChanged("BIST bulletin ZIP has no CSV/TXT entry")
                raw = zf.read(names[0])
        except zipfile.BadZipFile as exc:
            raise SchemaChanged("invalid BIST bulletin ZIP") from exc

        rows = list(csv.reader(StringIO(self._decode(raw)), delimiter=";"))
        rows = [row for row in rows if any(str(v).strip() for v in row)]
        if len(rows) < 2:
            raise SchemaChanged("empty BIST bulletin")
        header = [str(x).strip() for x in rows[0]]
        h = {name: i for i, name in enumerate(header)}
        code_i = h.get("ISLEM  KODU", h.get("ISLEM KODU"))
        close_i = h.get("KAPANIS FIYATI")
        group_i = h.get("ENSTRUMAN GRUBU")
        date_i = h.get("TARIH")
        volume_i = h.get("TOPLAM ISLEM ADEDI")
        if code_i is None or close_i is None or group_i is None or date_i is None:
            raise SchemaChanged("required BIST bulletin columns missing")

        prices: dict[str, dict] = {}
        for row in rows[1:]:
            if max(code_i, close_i, group_i, date_i) >= len(row):
                continue
            code = str(row[code_i]).strip().upper()
            group = str(row[group_i]).strip().upper()
            trade_date = str(row[date_i]).strip()
            if group != "EQT" or not code.endswith(".E") or trade_date != self.trade_date:
                continue
            close = self._num(row[close_i])
            if close is None or close <= 0:
                continue
            ticker = code[:-2]
            volume = self._num(row[volume_i]) if volume_i is not None and volume_i < len(row) else None
            prices[ticker] = {"close": close, "volume": volume}
        if not prices:
            raise SchemaChanged("no EQT .E prices found in BIST bulletin")
        self._prices = prices

    def get_latest_price(self, ticker: str) -> PriceObservation:
        if self._prices is None:
            self._fetch()
        symbol = ticker.replace(".IS", "").upper()
        row = (self._prices or {}).get(symbol)
        if not row:
            raise ProviderError(f"ticker {symbol} absent from BIST bulletin {self.trade_date}")
        return PriceObservation(
            ticker=symbol,
            market="BIST",
            trade_date=self.trade_date,
            timestamp=f"{self.trade_date}T18:10:00+03:00",
            close=float(row["close"]),
            currency="TRY",
            adjusted=False,
            volume=row.get("volume"),
            provider_id=self.provider_id,
            upstream_vendor=self.upstream_vendor,
            source_url=self._source_url or self._url(),
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        )
