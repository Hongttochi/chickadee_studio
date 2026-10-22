// Exercise the actual Electron executable over its native Chromium/Node inspectors.
const {spawn} = require('node:child_process');
const {chromium} = require('playwright');
async function launch({executablePath = require('electron'), args = [], env = process.env, timeout = 60000} = {}) {
  const child = spawn(executablePath, ['--inspect=0', '--remote-debugging-port=0', ...args], {
    env: Object.fromEntries(Object.entries(env).filter(([key]) => key !== 'ELECTRON_RUN_AS_NODE')),
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let output = '', browser, socket, sequence = 0;
  const pending = new Map();
  const exited = new Promise(resolve => child.once('exit', resolve));
  child.stdout.on('data', chunk => { output = (output + chunk).slice(-20000); });
  try {
    const endpoints = await new Promise((resolve, reject) => {
      let node, chrome;
      const timer = setTimeout(() => reject(new Error('Native inspectors did not start: ' + output)), timeout);
      child.once('error', error => { clearTimeout(timer); reject(error); });
      child.once('exit', code => { clearTimeout(timer); reject(new Error('Native app exited ' + code + ': ' + output)); });
      child.stderr.on('data', chunk => {
        output = (output + chunk).slice(-20000);
        node ||= output.match(/Debugger listening on (ws:\/\/[^\s]+)/)?.[1];
        chrome ||= output.match(/DevTools listening on (ws:\/\/[^\s]+)/)?.[1];
        if (node && chrome) { clearTimeout(timer); resolve({node, chrome}); }
      });
    });
    socket = new WebSocket(endpoints.node);
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Node inspector connection timeout')), timeout);
      socket.addEventListener('open', () => { clearTimeout(timer); resolve(); }, {once:true});
      socket.addEventListener('error', () => { clearTimeout(timer); reject(new Error('Node inspector connection failed')); }, {once:true});
    });
    socket.addEventListener('message', event => {
      const message = JSON.parse(event.data), request = pending.get(message.id);
      if (!request) return;
      pending.delete(message.id); clearTimeout(request.timer);
      if (message.error || message.result?.exceptionDetails) request.reject(new Error(JSON.stringify(message.error || message.result.exceptionDetails)));
      else request.resolve(message.result?.result?.value);
    });
    const evaluate = (fn, arg) => new Promise((resolve, reject) => {
      const id = ++sequence;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error('Native evaluation timeout')); }, timeout);
      pending.set(id, {resolve, reject, timer});
      socket.send(JSON.stringify({id, method:'Runtime.evaluate', params:{expression:`(${fn.toString()})(process.mainModule.require('electron'), ${JSON.stringify(arg) || 'undefined'})`, awaitPromise:true, returnByValue:true}}));
    });
    browser = await chromium.connectOverCDP(endpoints.chrome, {timeout});
    const context = browser.contexts()[0];
    return {
      process: () => child,
      firstWindow: async () => context.pages()[0] || await context.waitForEvent('page', {timeout}),
      waitForEvent: () => context.waitForEvent('page', {timeout}),
      evaluate,
      close: async () => {
        if (child.exitCode !== null || child.signalCode !== null) { socket.close(); await browser.close(); return; }
        // Let app shutdown persist state and stop its Python child before releasing the profile.
        await evaluate(({app}) => { setTimeout(() => app.quit(), 0); });
        socket.close();
        await browser.close();
        let timer;
        try { await Promise.race([exited, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('Native app shutdown timeout: ' + output)), 30000); })]); }
        finally { clearTimeout(timer); if (child.exitCode === null && child.signalCode === null) child.kill(); }
      },
    };
  } catch (error) {
    socket?.close(); await browser?.close().catch(() => {}); child.kill(); throw error;
  }
}
module.exports = {launch};
