const {test}=require('node:test');
const assert=require('node:assert/strict');
const {startupGroqConfig}=require('../electron/groq-env.cjs');
test('does not discover keys or read files without explicit user flag',async()=>{
 assert.equal(await startupGroqConfig(['app.exe'],()=>{throw Error('must not read');}),null);
});
test('reads only GROQ_API_KEY as inert data without interpolation or execution',async()=>{
 const key='gsk_test_0123456789';
 assert.deepEqual(await startupGroqConfig(['app.exe','--groq-env-file','.env'],async()=>`OTHER_KEY=ignored\nexport GROQ_API_KEY="${key}"\nMODEL=ignored`),{api_key:key});
 for(const text of ['GROQ_API_KEY=$(command)','GROQ_API_KEY=${OTHER_KEY}',`GROQ_API_KEY=${key}\nGROQ_API_KEY=${key}`,'OTHER_KEY=ignored'])
  await assert.rejects(startupGroqConfig(['app','--groq-env-file','.env'],async()=>text));
});
test('rejects missing/duplicate file flags, oversized and unreadable files without leaking content',async()=>{
 await assert.rejects(startupGroqConfig(['app','--groq-env-file']));
 await assert.rejects(startupGroqConfig(['app','--groq-env-file','a','--groq-env-file','b']));
 await assert.rejects(startupGroqConfig(['app','--groq-env-file','a'],async()=> 'x'.repeat(17000)));
 await assert.rejects(startupGroqConfig(['app','--groq-env-file','a'],async()=>{throw Error('private detail');}),e=>!e.message.includes('private detail'));
});
