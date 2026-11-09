import test from 'node:test';
import assert from 'node:assert/strict';
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
