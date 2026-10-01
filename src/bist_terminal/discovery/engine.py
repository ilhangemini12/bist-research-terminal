from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from bist_terminal.providers.spk import SPKRegistryProvider
from bist_terminal.providers.tspb import TSPBMembersProvider


class DiscoveryEngine:
    """Official-registry-first monthly discovery.

    Providers are isolated: one registry outage must not erase results from the
    other official registries. The snapshot records source status/errors rather
    than looping or bypassing access controls.
    """

    def __init__(self, spk=None, tspb=None):
        self.spk = spk or SPKRegistryProvider()
        self.tspb = tspb or TSPBMembersProvider()

    @staticmethod
    def _safe_call(label, fn):
        try:
            return {"status":"ACTIVE","data":fn(),"error":None}
        except Exception as exc:
            return {"status":"DEGRADED","data":[],"error":f"{type(exc).__name__}: {exc}"}

    def official_institutions(self) -> dict[str, Any]:
        brokers=self._safe_call("spk_brokers", self.spk.broker_list)
        banks=self._safe_call("spk_banks", self.spk.bank_list)
        tspb_url=self._safe_call("tspb_url", self.tspb.discover_workbook_url)
        if tspb_url["status"]=="ACTIVE":
            url=tspb_url["data"]
            tspb_members=self._safe_call("tspb_members", lambda:self.tspb.members(url))
        else:
            url=None; tspb_members={"status":"DEGRADED","data":[],"error":tspb_url["error"]}
        return {
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "sources": {
                "spk_brokers": {"status":brokers["status"],"count":len(brokers["data"]) if isinstance(brokers["data"],list) else None,"error":brokers["error"]},
                "spk_banks": {"status":banks["status"],"count":len(banks["data"]) if isinstance(banks["data"],list) else None,"error":banks["error"]},
                "tspb_members": {"status":tspb_members["status"],"count":len(tspb_members["data"]),"workbook_url":url,"error":tspb_members["error"]},
            },
            "brokers": brokers["data"],
            "banks": banks["data"],
            "tspb_members": tspb_members["data"],
        }

    def snapshot(self, path='data/discovery/institutions.json'):
        data=self.official_institutions()
        p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
        return data
