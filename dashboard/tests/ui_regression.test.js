const assert=require('assert');
const fs=require('fs');
const path=require('path');
const vm=require('vm');
const root=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const css=fs.readFileSync(path.join(root,'styles.css'),'utf8');
const app=fs.readFileSync(path.join(root,'app.js'),'utf8');

assert(html.indexOf('id="strategyOutput"')>0,'strategy output container missing');
assert(html.indexOf('id="strategyOutput"')<html.indexOf('id="presetCards"'),'strategy output must be above preset cards');
assert(css.includes('#stockTable .stock-ticker-col'),'ticker sticky CSS missing');
assert(css.includes('#stockTable thead th{position:sticky'),'sticky header CSS missing');
assert(!css.includes('th{position:relative}.drawer'),'legacy th relative override still present');
assert(app.includes('class="stock-star-col"'),'watch column sticky class missing');
assert(app.includes("c==='ticker'?'stock-ticker-col':''"),'ticker sticky class not rendered');
assert(app.includes("output?.classList.remove('hidden')"),'strategy output is not revealed');
assert(app.includes("scrollIntoView({behavior:'smooth',block:'start'})"),'mobile strategy feedback scroll missing');
assert(app.includes('type="button" data-runpreset'),'preset run buttons need explicit button type');
assert(app.includes("'target_price'"),'target price field missing from dashboard');
assert(app.includes("'target_source_count'"),'target source-count field missing from dashboard');
assert(app.includes("'model_portfolio_active'"),'model portfolio flag missing from dashboard');

// Execute the entire browser entry point. Source-string checks and node --check
// cannot detect top-level references accidentally moved outside function scope.
async function startupRegression(){
  const nodes=new Map();
  function element(id){
    const classes=new Set();
    return {id,value:'',innerHTML:'',textContent:'',dataset:{},style:{setProperty(){}},
      classList:{add(...items){items.forEach(x=>classes.add(x))},remove(...items){items.forEach(x=>classes.delete(x))},
        contains(x){return classes.has(x)},toggle(x,on){if(on??!classes.has(x))classes.add(x);else classes.delete(x)}},
      querySelectorAll(){return []},insertAdjacentHTML(_where,value){this.innerHTML+=value},
      scrollIntoView(){this.scrolled=true}};
  }
  for(const match of html.matchAll(/\bid="([^"]+)"/g))nodes.set(match[1],element(match[1]));
  const main=element('main');
  const document={getElementById(id){return nodes.get(id)||null},
    querySelector(selector){return selector==='main'?main:selector.startsWith('#')?nodes.get(selector.slice(1))||null:null},
    querySelectorAll(){return []},body:element('body'),documentElement:element('html')};
  const payload={mode:'LIVE_PIPELINE',stocks:[{ticker:'TEST',trade_date:'2026-10-09',price:10,price_status:'VERIFIED_2X',pe:8,rsi14:30}],
    sources:[],kap_news:[],summary:{tracked_stocks:1,verified_price_count:1},data_as_of:{prices:'2026-10-09'}};
  const context=vm.createContext({document,structuredClone,
    localStorage:{getItem(){return null},setItem(){}},matchMedia(){return {matches:false}},
    window:{matchMedia(){return {matches:true}},addEventListener(){}},navigator:{onLine:true},requestAnimationFrame(callback){callback()},
    fetch:async()=>({ok:true,json:async()=>payload}),SafeFormula:require(path.join(root,'formula.js'))});
  vm.runInContext(fs.readFileSync(path.join(root,'research.js'),'utf8'),context,{filename:'research.js'});
  vm.runInContext(app,context,{filename:'app.js'});
  await new Promise(resolve=>setImmediate(resolve));
  assert(!nodes.get('banner').textContent.startsWith('Data load failed:'),nodes.get('banner').textContent);
  assert(nodes.get('asof').textContent.includes('2026-10-09'),'boot did not render canonical data date');
  assert(nodes.get('stockTable').innerHTML.includes('TEST'),'boot did not render stock rows');
  nodes.get('strategyOutput').classList.add('hidden');
  vm.runInContext("runStrategy('Startup regression','pe < 10')",context);
  assert(nodes.get('strategyStatus').textContent.includes('1/1 matched'),'strategy did not execute');
  assert(!nodes.get('strategyOutput').classList.contains('hidden'),'strategy output remained hidden');
  assert(nodes.get('strategyOutput').scrolled,'mobile strategy result was not brought into view');
  nodes.get('quickMode').value='all';
  await nodes.get('quickForm').onsubmit({preventDefault(){}});
  assert(nodes.get('quickStatus').textContent.includes('1/1 hisse'),'quick Run did not scan current published data');
  assert(nodes.get('quickResults').innerHTML.includes('TEST'),'quick Run did not render result card');
  context.navigator.onLine=false;
  await nodes.get('quickForm').onsubmit({preventDefault(){}});
  assert(nodes.get('quickStatus').textContent.includes('Tarama yapılamadı'),'offline quick Run did not fail');
  assert.equal(nodes.get('quickResults').innerHTML,'','offline quick Run left stale results');
  assert.equal(nodes.get('quickRun').disabled,false,'Run stayed disabled after failure');
}
startupRegression().then(()=>console.log('ui regression tests passed')).catch(error=>{console.error(error);process.exitCode=1});
