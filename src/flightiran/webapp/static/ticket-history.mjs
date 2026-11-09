const ms=86400000;
export function parseHistory(raw,now=Date.now()) {
 const day=s=>typeof s==='string'&&/^\d{4}-\d\d-\d\d$/.test(s)&&Number.isFinite(Date.parse(s))&&new Date(s).toISOString().slice(0,10)===s?Date.parse(s)/ms:NaN;
 const end=day(raw?.as_of),start=end-20;
 if(raw?.currency!=='TOMAN'||raw.metric!=='daily_minimum'||raw.days!==21||
    typeof raw.origin!=='string'||!raw.origin||typeof raw.destination!=='string'||!raw.destination||
    !Number.isFinite(end)||end>Math.floor(now/ms)||!Array.isArray(raw.points)||raw.points.length>21)throw Error('Invalid history');
 let previous=-Infinity;const points=raw.points.map(p=>{
  const n=day(p.day),when=Date.parse(p.last_observed_at);
  if(!Number.isFinite(n)||n<start||n>end||n<=previous||!Number.isSafeInteger(p.price_toman)||p.price_toman<=0||p.price_toman>1e12||
    !Number.isSafeInteger(p.sample_count)||p.sample_count<=0||!Number.isFinite(when)||when>now+300000||
    Math.floor(when/ms)!==n)throw Error('Invalid history point');
  previous=n;return {...p,ordinal:n};
 });
 const observed=points.length?Math.max(...points.map(p=>Date.parse(p.last_observed_at))):null;
 if((observed===null?raw.observed_at!==null:Date.parse(raw.observed_at)!==observed))throw Error('Invalid observation time');
 const min=points.length?Math.min(...points.map(p=>p.price_toman)):null,max=points.length?Math.max(...points.map(p=>p.price_toman)):null;
 const plot=points.map(p=>({...p,x:22+(p.ordinal-start)*13.6,y:max===min?70:103-(p.price_toman-min)*66/(max-min)}));
 const segments=plot.slice(1).flatMap((p,i)=>p.ordinal===plot[i].ordinal+1?[[plot[i],p]]:[]);
 return {...raw,points:plot,segments,min,max,samples:points.reduce((s,p)=>s+p.sample_count,0),
  stale:raw.stale!==false||observed===null||now-observed>10800000,start,end};
}
