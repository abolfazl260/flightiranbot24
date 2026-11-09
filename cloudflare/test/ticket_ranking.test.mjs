import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {pricesAreStale} from '../../src/flightiran/webapp/static/ticket-ranking.mjs';
import {rankTicketFares,validDropPercent} from '../../src/flightiran/webapp/static/ticket-ranking.mjs';
const fare=(name,p,a,n=3)=>({name,price_toman:p,average_price_toman:a,average_sample_count:n,change_percent:-99});
test('verified drops reject missing, invalid, low sample and increasing prices',()=>{
  for(const f of [fare('a',10,20,2),fare('a',10,0),fare('a',10,-20),fare('a',10,null),
    fare('a',10,Infinity),fare('a',10,NaN),fare('a',10,9),fare('a',0,20),fare('a',10,20,2.5)])
    assert.equal(validDropPercent(f),null);
  assert.equal(validDropPercent(fare('a',80,100)),20);
  assert.equal(validDropPercent(fare('a',2,3)),33.3);
});
test('tabs preserve all valid cheapest rates, filter first and break equal drops by price then route',()=>{
 const routes=[{origin:'B',destinations:[fare('Y',80,100),fare('X',40,50),fare('Z',1,null)]},
 {origin:'A',destinations:[fare('X',40,50),fare('D',60,100),fare('invalid',-1,10)]}];
 const ids=x=>x.map(f=>f.origin+'/'+f.name);
 assert.deepEqual(ids(rankTicketFares(routes,{mode:'drops'})),['A/D','A/X','B/X','B/Y']);
 assert.deepEqual(ids(rankTicketFares(routes)),['B/Z','A/X','B/X','A/D','B/Y']);
 assert.deepEqual(ids(rankTicketFares(routes,{mode:'drops',origin:'B',search:'x'})),['B/X']);
 assert.deepEqual(rankTicketFares(routes,{mode:'drops',search:'missing'}),[]);
});

test('shared fixture matches all three platforms including top N, stable identities and half-up tenths',()=>{
 const fixture=JSON.parse(fs.readFileSync(new URL('../../docs/fixtures/ticket-ranking-v1.json',import.meta.url)));
 const ids=rows=>rows.map(f=>f.origin+'/'+f.name);
 const drops=rankTicketFares(fixture.routes,{mode:'drops'});
 assert.deepEqual(ids(drops),fixture.expected_drops);
 assert.deepEqual(drops.map(validDropPercent),fixture.expected_percentages);
 assert.deepEqual(ids(rankTicketFares(fixture.routes)),fixture.expected_cheap);
 assert.equal(validDropPercent({...fare('a',79,80),historical_average_toman:80.25}),1.6);
});
test('freshness fails conservatively for expired, future, missing and explicit stale data',()=>{
 const now=Date.now(),p={stale:false,observed_at:new Date(now).toISOString()};
 assert.equal(pricesAreStale(p,now),false);
 for(const q of [{...p,stale:true},{...p,observed_at:'bad'},
  {...p,observed_at:new Date(now-10800001).toISOString()},
  {...p,observed_at:new Date(now+300001).toISOString()}]) assert.equal(pricesAreStale(q,now),true);
});
