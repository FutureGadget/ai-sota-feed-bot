#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

async function readStdin() {
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  return Buffer.concat(chunks).toString('utf8');
}

async function main() {
  const raw = await readStdin();
  const req = JSON.parse(raw || '{}');
  const cfg = req.cfg || {};

  const { getOAuthApiKey } = await import('@mariozechner/pi-ai');

  const authFile = cfg.oauth_auth_file || 'data/llm/auth.json';
  if (!fs.existsSync(authFile)) throw new Error(`missing_auth_file:${authFile}`);
  const auth = JSON.parse(fs.readFileSync(authFile, 'utf8'));

  const provider = cfg.oauth_provider || 'openai-codex';
  const oauth = await getOAuthApiKey(provider, auth);
  if (!oauth || !oauth.apiKey) throw new Error('oauth_api_key_unavailable');

  // persist refreshed credentials if returned
  if (oauth.newCredentials) {
    auth[provider] = oauth.newCredentials;
    fs.mkdirSync(path.dirname(authFile), { recursive: true });
    fs.writeFileSync(authFile, JSON.stringify(auth, null, 2));
  }

  const endpoint = cfg.endpoint || 'https://api.openai.com/v1/chat/completions';
  const model = cfg.model || 'gpt-4o-mini';

  let systemPrompt = req.system || 'Return strict JSON only.';
  let userPayload = req.payload || {};

  const body = {
    model,
    temperature: 0,
    response_format: { type: 'json_object' },
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: JSON.stringify(userPayload) },
    ],
  };

  const res = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${oauth.apiKey}`,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`llm_http_${res.status}:${t.slice(0,300)}`);
  }
  const json = await res.json();
  const content = json?.choices?.[0]?.message?.content || '{}';
  process.stdout.write(content);
}

main().catch((e) => {
  console.error(String(e?.message || e));
  process.exit(1);
});
