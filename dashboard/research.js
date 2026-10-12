(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;root.ResearchTerminal=api})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const finite=x=>typeof x==='number'&&Number.isFinite(x),positive=x=>finite(x)&&x>0;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number=x=>finite(x)?x.toLocaleString('tr-TR',{maximumFractionDigits:2}):'N/A';
const percent=x=>finite(x)?number(x*100)+'%':'N/A';
const MODES={value:'Sektörüne göre ucuz',quality:'Değer + kalite',dividend:'Temettü',recovery:'RSI toparlanması',trend:'Trend',all:'Tüm doğrulanmış hisseler'};
function analyse(row,expected,options={}){
 const validDate=typeof expected==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(expected)&&Number.isFinite(Date.parse(expected));
 const fresh=validDate&&row.technical_freshness==='FRESH'&&row.technical_data_date===expected;
 const verified=validDate&&row.price_status==='VERIFIED_2X'&&row.trade_date===expected&&positive(row.price);
 const financial=row.financial_status==='PARSED_HIGH_CONFIDENCE'&&row.valuation_status==='ACTIVE';
 const cheap=financial&&positive(row.pe)&&positive(row.pb)&&positive(row.sector_pe_median)&&positive(row.sector_pb_median)&&row.pe<row.sector_pe_median&&row.pb<row.sector_pb_median;
 const quality=cheap&&finite(row.roe)&&finite(row.sector_roe_median)&&row.roe>row.sector_roe_median&&positive(row.net_income_ttm);
 const recovery=fresh&&finite(row.rsi_recent_low)&&row.rsi_recent_low<35&&finite(row.rsi14)&&finite(row.rsi14_prev)&&row.rsi14>row.rsi14_prev&&positive(row.volume_ma20)&&row.volume>row.volume_ma20&&row.price>row.sma10;
 const trend=fresh&&positive(row.sma20)&&positive(row.sma50)&&row.price>row.sma20&&row.sma20>row.sma50&&finite(row.roc20)&&row.roc20>0;
 const rules={value:cheap,quality,dividend:positive(row.dividend_yield),recovery,trend,all:true};
 let matched=verified&&Boolean(rules[options.mode||'value']);
 for(const [key,limit] of [['pe',options.peMax],['pb',options.pbMax],['rsi14',options.rsiMax]])if(finite(limit))matched=matched&&finite(row[key])&&row[key]<=limit&&(key==='rsi14'?fresh:financial);
 if(finite(options.roeMin))matched=matched&&financial&&finite(row.roe)&&row.roe>=options.roeMin/100;
 if(finite(options.debtMax))matched=matched&&financial&&finite(row.net_debt_ebitda)&&row.net_debt_ebitda<=options.debtMax;
 const margin=finite(options.margin)?Math.max(0,Math.min(80,options.margin)):20;
 const reference=financial&&positive(row.pe)&&positive(row.pb)&&positive(row.sector_pe_median)&&positive(row.sector_pb_median)?Math.min(row.price*row.sector_pe_median/row.pe,row.price*row.sector_pb_median/row.pb):null;
 const scenario=positive(reference)?reference*(1-margin/100):null;
 const band=fresh&&positive(row.sma20)&&positive(row.atr14)&&row.sma20-1.5*row.atr14>0?{low:row.sma20-.5*row.atr14,high:row.sma20+.5*row.atr14,invalidation:row.sma20-1.5*row.atr14}:null;
 return {matched,cheap,quality,recovery,trend,scenario,margin,band,discount:cheap?1-row.pe/row.sector_pe_median:null};
}
function scan(payload,options){const date=payload.data_as_of?.prices;if(payload.health?.expected_market_date&&date!==payload.health.expected_market_date)return [];return (payload.stocks||[]).map(row=>({row,analysis:analyse(row,date,options)})).filter(x=>x.analysis.matched).sort((a,b)=>(b.analysis.discount??-Infinity)-(a.analysis.discount??-Infinity)||a.row.ticker.localeCompare(b.row.ticker));}
function card({row:r,analysis:a}){
 const metrics=[['Fiyat (TL)',number(r.price)],['F/K',number(r.pe)],['PD/DD',number(r.pb)],['FD/FAVÖK',number(r.ev_ebitda)],['ROE',percent(r.roe)],['ROIC',percent(r.roic)],['Net borç/FAVÖK',number(r.net_debt_ebitda)],['Serbest nakit akışı verimi',percent(r.fcf_yield)],['Temettü verimi',percent(r.dividend_yield)],['RSI14',number(r.rsi14)]];
 return `<article class="research-card"><h3>${esc(r.ticker)} <small>${esc(r.sector)}</small></h3><p>${[a.cheap?'Sektörüne göre ucuz':null,a.quality?'Kalite koşulu sağlandı':null,a.recovery?'RSI toparlanması':null,a.trend?'Yükselen trend':null].filter(Boolean).join(' · ')||'Doğrulanmış kapanış'}</p><div class="metric-grid">${metrics.map(([k,v])=>`<div><span>${k}</span><b>${v}</b></div>`).join('')}</div><details><summary>Alım senaryosu ve finansal ayrıntılar</summary><p><b>Çarpan senaryosu:</b> ${number(a.scenario)} TL. Sektör medyanlarına göre hesaplanan iki fiyatın düşüğü üzerinden %${a.margin} iskonto. Gerçek değer veya fiyat hedefi değildir; sektör sınıfları geniş olabilir.</p><p><b>Teknik izleme bandı:</b> ${a.band?`${number(a.band.low)} – ${number(a.band.high)} TL; senaryonun bozulma seviyesi ${number(a.band.invalidation)} TL.`:'N/A — yeterli güncel SMA20/ATR14 yok.'} SMA20 ± 0,5 ATR14; bozulma SMA20 − 1,5 ATR14. Bu bir test edilmiş alım sinyali veya emir değildir.</p><p>Finansal dönem: ${esc(r.financial_report_period||'N/A')} · Baz: ${esc(r.valuation_basis||'N/A')} · Sermaye gözlemi: ${esc(r.capital_retrieved_at||'N/A')} · Teknik tarih: ${esc(r.technical_data_date||'N/A')}</p><p>Broker hedefi: ${number(r.target_price)} TL · Kaynak sayısı: ${number(r.target_source_count)}. Tek broker konsensüs değildir.</p><details><summary>Tüm veri alanları ve kaynak bilgisi</summary><dl class="raw-metrics">${Object.entries(r).map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v==null?'N/A':typeof v==='object'?JSON.stringify(v):v)}</dd>`).join('')}</dl></details></details></article>`;
}
function freshness(payload,now=Date.now()){
 const generated=Date.parse(payload.generated_at),age=now-generated;
 const date=payload.data_as_of?.prices,expected=payload.health?.expected_market_date;
 const notices=[];
 if(!date||!/^\d{4}-\d{2}-\d{2}$/.test(date))notices.push('Kapanış tarihi eksik/geçersiz; doğrulanmış tarama kullanılamaz.');
 if(expected&&date!==expected)notices.push('Kapanış tarihi beklenen işlem gününden farklı; doğrulanmış tarama kullanılamaz.');
 if(!Number.isFinite(generated))notices.push('Üretim zamanı bilinmiyor.');
 else if(age< -300000)notices.push('Üretim zamanı gelecekte; saat/veri kontrolü gerekli.');
 else if(age>36*3600000)notices.push('Üretim 36 saatten eski; veri yeniliği teyit edilmeli.');
 return notices.join(' ');
}
function mount(initial,onPayload){
 const host=document.getElementById('quickResults'),button=document.getElementById('quickRun'),status=document.getElementById('quickStatus');if(!host||!button)return;
 const read=id=>{const s=document.getElementById(id).value.trim();return s===''?undefined:Number(s)};
 const run=async event=>{event?.preventDefault();return execute()};
 const execute=async()=>{button.disabled=true;host.innerHTML='';status.textContent='Son yayımlanan veri alınıyor…';try{
  if(!navigator.onLine)throw Error('Çevrimdışı');
  const response=await fetch('data/latest.json',{cache:'no-store'});if(!response.ok)throw Error('HTTP '+response.status);const payload=await response.json();if(!Array.isArray(payload.stocks)||!payload.stocks.length)throw Error('Veri kümesi boş');
  if(!payload.data_as_of?.prices)throw Error('Kapanış tarihi eksik');
  if(!navigator.onLine)throw Error('Bağlantı kesildi');
  if(onPayload)onPayload(payload);
  const options={mode:document.getElementById('quickMode').value,peMax:read('quickPE'),pbMax:read('quickPB'),rsiMax:read('quickRSI'),roeMin:read('quickROE'),debtMax:read('quickDebt'),margin:read('quickMargin')};
  for(const v of Object.values(options))if(typeof v==='number'&&!Number.isFinite(v))throw Error('Geçerli sayısal sınır girin');
  const matches=scan(payload,options);const warning=freshness(payload);
  status.textContent=`${MODES[options.mode]}: ${matches.length}/${payload.stocks.length} hisse. Kapanış: ${payload.data_as_of.prices}. Son üretim: ${payload.generated_at}. ${warning?'UYARI: '+warning+' ':''}Run sunucu veri toplamasını tetiklemez; yayımlanmış veriyi yeniden okur ve tarar.`;
  host.innerHTML=matches.length?matches.map(card).join(''):'<p>Bu koşullara uyan doğrulanmış hisse yok. Boş bıraktığın sınırlar uygulanmaz.</p>';
 }catch(e){status.textContent='Tarama yapılamadı: '+e.message+'. İnternet bağlantısını ve veri durumunu kontrol et; eski veriyle sonuç üretilmedi.'}finally{button.disabled=false}};
 const form=document.getElementById('quickForm');if(form)form.onsubmit=run;else button.onclick=run;
 window.addEventListener('offline',()=>{host.innerHTML='';status.textContent='Çevrimdışısınız. Tarama sonuçları temizlendi. Bağlantı gelince Run / Tara ile yeniden okuyun.'});
 status.textContent=`Hazır. Son kapanış: ${initial.data_as_of?.prices||'N/A'}. Bir tarama seçip Run / Tara düğmesine bas.`;

}
return {analyse,scan,mount,card,MODES,freshness};
});
