(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  root.SafeFormula=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const tokenRe=/\s*(?:(\d+(?:\.\d+)?)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|([A-Za-z_][A-Za-z0-9_]*)|(\*\*|==|!=|<=|>=|[()+\-*/%<>]))/gy;
  function tokenize(input){
    const out=[]; let pos=0;
    while(pos<input.length){
      tokenRe.lastIndex=pos; const m=tokenRe.exec(input);
      if(!m||m.index!==pos) throw new Error('Unsupported token near: '+input.slice(pos,pos+20));
      pos=tokenRe.lastIndex;
      if(m[1]) out.push({t:'num',v:Number(m[1])});
      else if(m[2]) out.push({t:'str',v:JSON.parse(m[2][0]==="'"?'"'+m[2].slice(1,-1).replace(/"/g,'\\"')+'"':m[2])});
      else if(m[3]){const w=m[3].toLowerCase(); if(['and','or','not'].includes(w))out.push({t:w,v:w}); else if(['true','false','null','none'].includes(w))out.push({t:'lit',v:w==='true'?true:w==='false'?false:null}); else out.push({t:'name',v:m[3]});}
      else out.push({t:'op',v:m[4]});
    }
    out.push({t:'eof',v:null}); return out;
  }
  class Parser{
    constructor(tokens,row){this.x=tokens;this.i=0;this.row=row||{};this.names=new Set()}
    cur(){return this.x[this.i]}
    take(t,v){let c=this.cur();if(c.t===t&&(v===undefined||c.v===v)){this.i++;return c}return null}
    need(t,v){let c=this.take(t,v);if(!c)throw new Error('Expected '+(v??t));return c}
    parse(){let v=this.or();this.need('eof');return v}
    or(){let v=this.and();while(this.take('or')){const r=this.and();v=Boolean(v)||Boolean(r)}return v}
    and(){let v=this.not();while(this.take('and')){const r=this.not();v=Boolean(v)&&Boolean(r)}return v}
    not(){if(this.take('not'))return !Boolean(this.not());return this.compare()}
    compare(){let left=this.add();while(this.cur().t==='op'&&['==','!=','<','<=','>','>='].includes(this.cur().v)){let op=this.cur().v;this.i++;let right=this.add();let ok=false;if(left!=null&&right!=null){if(op==='==')ok=left===right;else if(op==='!=')ok=left!==right;else if(op==='<')ok=left<right;else if(op==='<=')ok=left<=right;else if(op==='>')ok=left>right;else ok=left>=right} else ok=op==='!='?left!==right:left===right; if(!ok)return false;left=right}return left}
    add(){let v=this.mul();while(this.cur().t==='op'&&['+','-'].includes(this.cur().v)){let op=this.cur().v;this.i++;let r=this.mul();v=this.math(op,v,r)}return v}
    mul(){let v=this.pow();while(this.cur().t==='op'&&['*','/','%'].includes(this.cur().v)){let op=this.cur().v;this.i++;let r=this.pow();v=this.math(op,v,r)}return v}
    pow(){let v=this.unary();if(this.take('op','**')){let r=this.pow();v=this.math('**',v,r)}return v}
    unary(){if(this.take('op','-')){let v=this.unary();return typeof v==='number'?-v:null}if(this.take('op','+')){let v=this.unary();return typeof v==='number'?v:null}return this.primary()}
    primary(){let c=this.cur();if(this.take('op','(')){let v=this.or();this.need('op',')');return v}if(c.t==='num'||c.t==='str'||c.t==='lit'){this.i++;return c.v}if(c.t==='name'){this.i++;this.names.add(c.v);return Object.prototype.hasOwnProperty.call(this.row,c.v)?this.row[c.v]:null}throw new Error('Unexpected token')}
    math(op,a,b){if(typeof a!=='number'||typeof b!=='number'||!Number.isFinite(a)||!Number.isFinite(b))return null;if((op==='/'||op==='%')&&b===0)return null;if(op==='+')return a+b;if(op==='-')return a-b;if(op==='*')return a*b;if(op==='/')return a/b;if(op==='%')return a%b;if(op==='**')return a**b;return null}
  }
  function evaluate(expr,row){const p=new Parser(tokenize(expr),row);let value=p.parse();return {matched:Boolean(value),value,names:[...p.names].sort()}}
  function explain(expr,row){const r=evaluate(expr,row);return {...r,inputs:Object.fromEntries(r.names.map(k=>[k,row?.[k]??null]))}}
  return {tokenize,evaluate,explain};
});
