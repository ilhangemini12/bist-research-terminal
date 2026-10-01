from __future__ import annotations
from datetime import datetime, timezone, timedelta
import time
import pandas as pd
import requests
from bist_terminal.models import PriceObservation
from bist_terminal.providers.base import BaseProvider, RateLimited, Blocked, SchemaChanged

class YahooChartProvider(BaseProvider):
    provider_id="yahoo_chart"
    upstream_vendor="Yahoo market data feed"
    def __init__(self, session=None, timeout=12):
        self.session=session or requests.Session(); self.timeout=timeout

    def _symbol(self,ticker:str)->str:
        return ticker if ticker.endswith('.IS') else ticker+'.IS'

    def _request_json(self, url:str):
        def request_once():
            r=self.session.get(url,timeout=self.timeout,headers={"User-Agent":"bist-research-terminal/0.3"})
            if r.status_code==429: raise RateLimited("Yahoo 429")
            if r.status_code in (401,403): raise Blocked(f"Yahoo {r.status_code}")
            r.raise_for_status(); return r
        return self.with_retry(request_once).json()

    def _chart_url(self,ticker:str,period1:int|None=None,period2:int|None=None,range_:str|None=None):
        symbol=self._symbol(ticker)
        base=f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&events=div%2Csplits"
        if range_: return base+f"&range={range_}"
        return base+f"&period1={int(period1)}&period2={int(period2)}"

    def get_latest_price(self,ticker:str)->PriceObservation:
        url=self._chart_url(ticker,range_='5d'); data=self._request_json(url)
        try:
            result=data['chart']['result'][0]; ts=result['timestamp']; q=result['indicators']['quote'][0]
            idx=max(i for i,v in enumerate(q['close']) if v is not None)
            dt=datetime.fromtimestamp(ts[idx],tz=timezone.utc); meta=result.get('meta',{})
            return PriceObservation(ticker=ticker.replace('.IS',''),market='BIST',trade_date=dt.date().isoformat(),timestamp=dt.isoformat(),close=float(q['close'][idx]),currency=meta.get('currency','TRY'),adjusted=False,volume=float(q['volume'][idx]) if q['volume'][idx] is not None else None,provider_id=self.provider_id,upstream_vendor=self.upstream_vendor,source_url=url,retrieved_at=datetime.now(timezone.utc).isoformat())
        except (KeyError,IndexError,TypeError,ValueError) as e: raise SchemaChanged(str(e)) from e

    def get_history(self,ticker:str,start:str,end:str)->pd.DataFrame:
        """Return daily OHLCV + adjusted close without fabricating missing fields."""
        s=datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
        # Yahoo period2 is exclusive; include requested end date.
        e=datetime.fromisoformat(end).replace(tzinfo=timezone.utc)+timedelta(days=1)
        url=self._chart_url(ticker,int(s.timestamp()),int(e.timestamp())); data=self._request_json(url)
        try:
            result=data['chart']['result'][0]; timestamps=result.get('timestamp') or []; q=result['indicators']['quote'][0]
            adj=(result.get('indicators',{}).get('adjclose') or [{}])[0].get('adjclose') or [None]*len(timestamps)
            rows=[]
            for i,ts in enumerate(timestamps):
                close=q.get('close',[None]*len(timestamps))[i]
                if close is None: continue
                dt=datetime.fromtimestamp(ts,tz=timezone.utc)
                rows.append({'Date':dt.date().isoformat(),'Open':q.get('open',[None]*len(timestamps))[i],'High':q.get('high',[None]*len(timestamps))[i],'Low':q.get('low',[None]*len(timestamps))[i],'Close':close,'Adjusted Close':adj[i] if i<len(adj) else None,'Volume':q.get('volume',[None]*len(timestamps))[i],'provider_id':self.provider_id,'upstream_vendor':self.upstream_vendor,'source_url':url})
            if not rows: return pd.DataFrame(columns=['Date','Open','High','Low','Close','Adjusted Close','Volume','provider_id','upstream_vendor','source_url'])
            return pd.DataFrame(rows).sort_values('Date').drop_duplicates('Date',keep='last').reset_index(drop=True)
        except (KeyError,IndexError,TypeError,ValueError) as e: raise SchemaChanged(str(e)) from e

    def get_corporate_actions(self,ticker:str,start:str,end:str)->pd.DataFrame:
        s=datetime.fromisoformat(start).replace(tzinfo=timezone.utc); e=datetime.fromisoformat(end).replace(tzinfo=timezone.utc)+timedelta(days=1)
        url=self._chart_url(ticker,int(s.timestamp()),int(e.timestamp())); data=self._request_json(url)
        try: events=(data['chart']['result'][0].get('events') or {})
        except (KeyError,IndexError,TypeError) as e: raise SchemaChanged(str(e)) from e
        rows=[]
        for kind,key in [('dividend','dividends'),('split','splits')]:
            for _,ev in (events.get(key) or {}).items():
                ts=ev.get('date');
                if not ts: continue
                row={'ticker':ticker.replace('.IS',''),'date':datetime.fromtimestamp(ts,tz=timezone.utc).date().isoformat(),'action_type':kind,'provider_id':self.provider_id,'source_url':url}
                if kind=='dividend': row.update(amount=ev.get('amount'),split_ratio=None)
                else: row.update(amount=None,split_ratio=ev.get('splitRatio') or ev.get('numerator'))
                rows.append(row)
        return pd.DataFrame(rows)
