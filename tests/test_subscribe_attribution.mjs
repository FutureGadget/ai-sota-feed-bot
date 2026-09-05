import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';


const source = fs.readFileSync(new URL('../web/subscribe.html', import.meta.url), 'utf8');

function extractFunction(name) {
  const asyncStart = source.indexOf(`async function ${name}(`);
  const start = asyncStart === -1 ? source.indexOf(`function ${name}(`) : asyncStart;
  assert.notEqual(start, -1, `missing ${name}`);
  const brace = source.indexOf(') {', start) + 2;
  let depth = 0;
  for (let index = brace; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1;
    if (source[index] === '}') depth -= 1;
    if (depth === 0) return source.slice(start, index + 1);
  }
  throw new Error(`unterminated ${name}`);
}

const message = { dataset: {}, hidden: true, textContent: '' };
const captured = [];
const stored = [];
const context = vm.createContext({
  Array,
  JSON,
  String,
  URL,
  URLSearchParams,
  document: { getElementById: () => message },
  localStorage: { setItem: (...args) => stored.push(args) },
  window: {
    location: { search: '?ref=skill_lab&lab_id=lab-debugging-skill' },
    aiFeedPostHog: { capture: (...args) => captured.push(args) },
  },
});
vm.runInContext("const ALLOWED_SUBSCRIBE_REFS = new Set(['skill_lab']);", context);
vm.runInContext("const LAB_ID_RE = /^lab-[a-z0-9][a-z0-9-]{0,76}$/;", context);
vm.runInContext("const EMAIL_SUBSCRIBED_KEY = 'ai_feed_email_subscribed_v1';", context);
vm.runInContext("const NUDGE_DONE_KEY = 'ai_feed_subscribe_nudge_done_v1';", context);
vm.runInContext(extractFunction('sanitizedSubscribePath'), context);
vm.runInContext(extractFunction('subscribeAttribution'), context);
vm.runInContext(extractFunction('captureSubscribeSuccess'), context);
vm.runInContext(extractFunction('shouldRecordSubscribeSuccess'), context);
vm.runInContext(extractFunction('markSubscribed'), context);
vm.runInContext(extractFunction('setMessage'), context);
vm.runInContext(extractFunction('submitForm'), context);

function signupForm(honeypot = '') {
  const button = { disabled: false, removed: false, remove() { this.removed = true; } };
  const cadence = [{ disabled: false }];
  cadence.value = 'both';
  const form = {
    elements: {
      cadence,
      email: { value: 'reader@example.com', disabled: false, focus() {} },
      website: { value: honeypot },
    },
    querySelector: () => button,
  };
  return { button, form };
}

test('subscribe sanitizer preserves only valid Skill Lab attribution', () => {
  assert.equal(
    context.sanitizedSubscribePath(
      'https://www.llm-digest.com/subscribe?ref=skill_lab&lab_id=lab-debugging-skill',
    ),
    '/subscribe?ref=skill_lab&lab_id=lab-debugging-skill',
  );
  assert.equal(
    context.sanitizedSubscribePath(
      'https://www.llm-digest.com/subscribe?ref=skill_lab&lab_id=alice@example.com',
    ),
    '/subscribe?ref=skill_lab',
  );
  assert.equal(
    context.sanitizedSubscribePath(
      'https://www.llm-digest.com/subscribe?email=alice@example.com#address',
    ),
    '/subscribe',
  );
  assert.equal(
    context.sanitizedSubscribePath(
      'https://www.llm-digest.com/subscribe?lab_id=lab-debugging-skill&utm_source=email',
    ),
    '/subscribe',
  );
});

test('honeypot responses never count as successful subscriptions', () => {
  assert.equal(context.shouldRecordSubscribeSuccess(''), true);
  assert.equal(context.shouldRecordSubscribeSuccess('   '), true);
  assert.equal(context.shouldRecordSubscribeSuccess('bot.example'), false);
});

test('successful submit records bounded attribution but never the email', async () => {
  captured.length = 0;
  stored.length = 0;
  context.fetch = async () => ({ ok: true, status: 200 });
  const { form } = signupForm();

  await context.submitForm(form);

  assert.equal(captured.length, 1);
  assert.equal(captured[0][0], 'subscribe_success');
  assert.deepEqual(
    JSON.parse(JSON.stringify(captured[0][1])),
    { cadence: 'both', ref: 'skill_lab', lab_id: 'lab-debugging-skill' },
  );
  assert.equal(JSON.stringify(captured).includes('reader@example.com'), false);
  assert.equal(stored.length, 2);
});

test('honeypot 200 keeps neutral success UI without recording a conversion', async () => {
  captured.length = 0;
  stored.length = 0;
  let submittedBody = null;
  context.fetch = async (_url, options) => {
    submittedBody = JSON.parse(options.body);
    return { ok: true, status: 200 };
  };
  const { button, form } = signupForm(' bot.example ');

  await context.submitForm(form);

  assert.equal(submittedBody.hp, 'bot.example');
  assert.equal(captured.length, 0);
  assert.equal(stored.length, 0);
  assert.equal(button.removed, true);
  assert.equal(message.dataset.state, 'ok');
});

test('subscribe sanitizer executes before PostHog can capture a page view', () => {
  assert.ok(
    source.indexOf('function sanitizedSubscribePath(rawHref)') <
      source.indexOf('src="/posthog-client.js'),
  );
});
