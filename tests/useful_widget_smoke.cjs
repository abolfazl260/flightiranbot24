// Execute the actual widget JS against its small documented DOM surface.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { states, html } = JSON.parse(fs.readFileSync(0, 'utf8'));
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

class Element {
  constructor() {
    this.children = [];
    this.handlers = {};
    this.style = {};
    this.hidden = false;
    this.text = '';
  }
  set textContent(text) { this.text = text; this.children = []; }
  get textContent() { return this.text; }
  appendChild(element) { this.children.push(element); }
  addEventListener(name, handler) { this.handlers[name] = handler; }
  click() { this.handlers.click(); }
}

const ids = {};
for (const match of html.matchAll(/id="([^"]+)"/g)) ids[match[1]] = new Element();
const calls = [];
let changed;
const widget = {
  chatData: JSON.stringify(states[0]),
  ready() {},
  onEvent(name, handler) { changed = handler; },
  request(action) {
    calls.push(action);
    return Promise.resolve({ result: 'accepted' });
  },
};
vm.runInNewContext(script, {
  window: { TelegramWidget: widget },
  document: {
    getElementById: id => ids[id],
    createElement: () => new Element(),
  },
});

function update(state) {
  widget.chatData = JSON.stringify(state);
  changed();
}

(async () => {
  assert.equal(ids.items.children.length, 7); // Six categories + all resources.
  ids.filters.click();
  await Promise.resolve();
  assert(calls.at(-1).endsWith(':filters'));

  update(states[1]);
  ids.items.children[1].click();
  await Promise.resolve();
  assert(calls.at(-1).includes(':detail:'));

  update(states[2]);
  assert.equal(ids.open.hidden, false);
  ids.open.click();
  await Promise.resolve();
  assert(calls.at(-1).endsWith(':open'));

  update({ ...states[2], error: 'خطا' });
  assert.equal(ids.body.textContent, states[2].text);
  assert.equal(ids.status.textContent, 'خطا');

  update({ ...states[2], text: '<script>alert(1)</script>' });
  assert.equal(ids.body.textContent, '<script>alert(1)</script>');
  assert.equal(ids.body.children.length, 0);
  console.log('Widget DOM: navigation, explicit source, retained content and text safety passed');
})().catch(error => { console.error(error); process.exit(1); });
