const {test}=require('node:test');
const assert=require('node:assert/strict');
test('Newest default uses observation time across findings and candidates without mutating saved results',async()=>{
 const {sortDetections}=await import('../src/result-list.mjs');
 const items=[{id:'f_1',_detail:{observed_at:'2026-10-23T12:00:00+09:00'}},
  {id:'f_2',_detail:{observed_at:'2026-10-23T12:02:00+09:00'}},
  {id:'c_1',observed_at:'2026-10-23T12:01:00+09:00'}];
 assert.deepEqual(sortDetections(items).map(r=>r.id),['f_2','c_1','f_1']);
 assert.deepEqual(sortDetections(items,'oldest').map(r=>r.id),['f_1','c_1','f_2']);
 assert.deepEqual(items.map(r=>r.id),['f_1','f_2','c_1']);
 assert.deepEqual(sortDetections([{id:'old1'},{id:'old2'}]).map(r=>r.id),['old2','old1']);
});
