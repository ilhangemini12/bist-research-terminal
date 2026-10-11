const assert=require('assert');
const {evaluate,explain}=require('../formula.js');
assert.equal(evaluate('pe < sector_pe_median * 0.8 and roe > 0.2',{pe:6,sector_pe_median:10,roe:.25}).matched,true);
assert.equal(evaluate('not (rsi14 > 40) or volume_ratio > 2',{rsi14:35,volume_ratio:1}).matched,true);
assert.equal(evaluate('sector == "Bank" and pb < 2',{sector:'Bank',pb:1.2}).matched,true);
assert.equal(evaluate('1 / 0 > 2',{}).matched,false);
assert.throws(()=>evaluate('alert(1)',{}));
assert.throws(()=>evaluate('x.constructor',{}));
const x=explain('pe < sector_pe_median',{pe:4,sector_pe_median:6});assert.deepEqual(x.inputs,{pe:4,sector_pe_median:6});
console.log('formula tests passed');

const comparisonApi=require('../formula.js');
for(const expr of ['pe > 0','pe > 0 and pb > 0','0 < pe < 20'])assert.strictEqual(comparisonApi.evaluate(expr,{pe:8,pb:0.5}).matched,true,expr);
assert.strictEqual(comparisonApi.evaluate('20 < pe < 30 or pb > 0',{pe:8,pb:0.5}).matched,true);
assert.strictEqual(comparisonApi.evaluate('a < b',{a:null,b:null}).matched,false);
assert.strictEqual(comparisonApi.evaluate('pe > 0 and pe < sector_pe_median and pb > 0 and pb < sector_pb_median',{pe:5.5,pb:0.43,sector_pe_median:15.4,sector_pb_median:0.97}).matched,true);
