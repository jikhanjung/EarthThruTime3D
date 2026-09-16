import {test} from 'node:test';
import assert from 'node:assert/strict';
import {bidiClient} from './firefox-bidi.mjs';
class Socket extends EventTarget {
  send(data) {this.sent = JSON.parse(data);}
  reply(data) {const event = new Event('message'); event.data = JSON.stringify(data); this.dispatchEvent(event);}
  close() {this.dispatchEvent(new Event('close'));}
}
test('BiDi rejects protocol errors and still handles the next response', async () => {
  const socket = new Socket(), client = bidiClient(socket);
  const bad = client.send('bad');
  socket.reply({id: socket.sent.id, type:'error', error:'invalid argument', message:'bad method'});
  await assert.rejects(bad, /invalid argument/);
  const good = client.send('good'); socket.reply({id:socket.sent.id, result:{ok:true}});
  assert.equal((await good).result.ok,true); client.close();
});
test('BiDi times out a command that never replies', async () => {
  const client = bidiClient(new Socket(), {timeoutMs:20});
  await assert.rejects(client.send('stalled'), /stalled timed out/); client.close();
});
test('BiDi close rejects all pending and future commands', async () => {
  const socket = new Socket(), client = bidiClient(socket);
  const one = assert.rejects(client.send('one'), /closed/);
  const two = assert.rejects(client.send('two'), /closed/);
  socket.close(); await Promise.all([one,two]);
  await assert.rejects(client.send('three'), /unavailable/);
});
