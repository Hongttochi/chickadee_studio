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
test('Slash groups preserve queries, origins, encoded slash segments, and all original records',async()=>{
 const {pathTreeRows}=await import('../src/result-list.mjs');
 const pages=['https://example.test/board/view?id=1','https://example.test/board/view?id=2',
  'https://example.test/board/sub/item','https://example.test/boardroom/list',
  'https://other.test/board/item','https://example.test/a%2Fb/item'].map(url=>({url}));
 const initial=pathTreeRows(pages);
 assert.equal(initial.filter(r=>r.kind==='page').length,6);
 assert.ok(initial.some(r=>r.kind==='group'&&r.label==='/a%2Fb'));
 const folded=pathTreeRows(pages,new Set(['https://example.test/board']));
 assert.equal(folded.filter(r=>r.kind==='page').length,3);
 assert.ok(folded.find(r=>r.page?.url.includes('boardroom')));
 const search=pathTreeRows(pages,new Set(['https://example.test','https://example.test/board']),'id=2');
 assert.equal(search.filter(r=>r.kind==='page').length,1);
 assert.equal(search.find(r=>r.kind==='page').page,pages[1]);
 assert.ok(search.filter(r=>r.kind==='group').every(r=>r.expanded));
});
