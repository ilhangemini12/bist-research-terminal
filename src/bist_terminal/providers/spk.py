from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

BASE = "https://ws.spk.gov.tr"


@dataclass(frozen=True)
class SPKEndpoint:
    path: str
    purpose: str


class SPKRegistryProvider:
    """Thin client for SPK's documented public OAS3 web services.

    The client deliberately returns the published JSON unchanged. Normalisation into
    terminal schemas happens downstream so a schema change is detectable instead of
    silently coerced into wrong financial values.
    """

    provider_id = "spk_ws"
    endpoints = {
        "brokers": SPKEndpoint("/AKBankaFaaliyet/api/AraciKurumListe", "broker registry"),
        "banks": SPKEndpoint("/AKBankaFaaliyet/api/BankaListe", "bank registry"),
        "activity_types": SPKEndpoint("/AKBankaFaaliyet/api/FaaliyetIzniTuru", "activity permission types"),
        "listed_companies": SPKEndpoint("/HalkaAcikSirket/api/Sirketler/Borsa", "listed public companies"),
        "disclosure_topics": SPKEndpoint("/CompanyData/api/OzelDurumAciklamalariKonular", "disclosure topics"),
        "disclosures": SPKEndpoint("/CompanyData/api/OzelDurumAciklamalari", "special disclosures"),
        "financial_topics": SPKEndpoint("/CompanyData/api/FinansalRaporlarKonular", "financial-report topics"),
        "financial_reports": SPKEndpoint("/CompanyData/api/FinansalRaporlar", "financial-report metadata"),
    }

    def __init__(self, session=None, timeout: int = 15):
        self.session = session or requests.Session()
        self.timeout = timeout

    def broker_list(self):
        return self._get(self.endpoints["brokers"].path)

    def bank_list(self):
        return self._get(self.endpoints["banks"].path)

    def activity_permission_types(self):
        return self._get(self.endpoints["activity_types"].path)

    def broker_activity_permissions(self, **params):
        return self._get("/AKBankaFaaliyet/api/AracıKurumFaaliyetIzinleri", params=params)

    def bank_activity_permissions(self, **params):
        return self._get("/AKBankaFaaliyet/api/BankaFaaliyetIzinleri", params=params)

    def listed_companies(self):
        return self._get(self.endpoints["listed_companies"].path)

    def disclosure_topics(self):
        return self._get(self.endpoints["disclosure_topics"].path)

    def special_disclosures(self, **params):
        """Query SPK special-disclosure metadata using documented query parameters.

        Examples of accepted SPK parameters include companyCode, subject,
        dateBegin and dateEnd. Unknown keys are passed through rather than guessed.
        """
        return self._get(self.endpoints["disclosures"].path, params=params)

    def special_disclosure(self, disclosure_id: int | str):
        return self._get(f"/CompanyData/api/OzelDurumAciklamalari/{disclosure_id}")

    def financial_report_topics(self):
        return self._get(self.endpoints["financial_topics"].path)

    def financial_reports(self, **params):
        """Query financial-report metadata. Does not fabricate statement values."""
        return self._get(self.endpoints["financial_reports"].path, params=params)

    def financial_report(self, report_id: int | str):
        return self._get(f"/CompanyData/api/FinansalRapor/{report_id}")

    def _get(self, path: str, params: dict[str, Any] | None = None):
        r = self.session.get(
            BASE + path,
            params=params or None,
            timeout=self.timeout,
            headers={"User-Agent": "bist-research-terminal/0.3 (+research; free-first)"},
        )
        r.raise_for_status()
        return r.json()
