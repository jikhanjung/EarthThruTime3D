// Bounded WebDriver BiDi commands; failures must reach the caller's cleanup path.
export function bidiClient(socket, {timeoutMs = 10000} = {}) {
  const pending = new Map(), events = [];
  let counter = 0, stopped = false;
  const fail = message => {
    stopped = true;
    for (const item of pending.values()) {clearTimeout(item.timer); item.reject(new Error(message));}
    pending.clear();
  };
  socket.addEventListener('close', () => fail('Firefox BiDi connection closed'));
  socket.addEventListener('error', () => fail('Firefox BiDi connection failed'));
  socket.addEventListener('message', message => {
    let data;
    try {data = JSON.parse(message.data);} catch {fail('Invalid Firefox BiDi response'); return;}
    const item = pending.get(data.id);
    if (item) {
      clearTimeout(item.timer); pending.delete(data.id);
      if (data.type === 'error') item.reject(new Error(`${item.method}: ${data.error}: ${data.message}`));
      else item.resolve(data);
    } else if (data.method) events.push(data);
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    if (stopped) {reject(new Error('Firefox BiDi connection is unavailable')); return;}
    const id = ++counter;
    const timer = setTimeout(() => {
      pending.delete(id); reject(new Error(`${method} timed out after ${timeoutMs} ms`));
    }, timeoutMs);
    pending.set(id, {resolve, reject, timer, method});
    try {socket.send(JSON.stringify({id, method, params}));}
    catch (error) {clearTimeout(timer); pending.delete(id); reject(error);}
  });
  return {send, events, close() {fail('Firefox BiDi client closed'); socket.close();}};
}
