#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { getModel, complete, getOAuthApiKey } from '@mariozechner/pi-ai';

async function readStdin() {
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  return Buffer.concat(chunks).toString('utf8');
}

function extractAssistantText(message) {
  const blocks = Array.isArray(message?.content) ? message.content : [];
  const texts = blocks.filter((b) => b?.type === 'text').map((b) => b.text || '');
  return texts.join('\n').trim();
}

async function main() {
  const raw = await readStdin();
  const req = JSON.parse(raw || '{}');
  const cfg = req.cfg || {};

  const authFile = cfg.oauth_auth_file || 'data/llm/auth.json';
  if (!fs.existsSync(authFile)) throw new Error(`missing_auth_file:${authFile}`);
  const auth = JSON.parse(fs.readFileSync(authFile, 'utf8'));

  const provider = cfg.oauth_provider || 'openai-codex';
  const oauth = await getOAuthApiKey(provider, auth);
  if (!oauth || !oauth.apiKey) throw new Error('oauth_api_key_unavailable');

  if (oauth.newCredentials) {
    auth[provider] = oauth.newCredentials;
    fs.mkdirSync(path.dirname(authFile), { recursive: true });
    fs.writeFileSync(authFile, JSON.stringify(auth, null, 2));
  }

  const providerForModel = cfg.model_provider || 'openai-codex';
  const modelId = cfg.model || 'gpt-5.3-codex';
  const model = getModel(providerForModel, modelId);

  const ctx = {
    systemPrompt: req.system || 'Return strict JSON only.',
    messages: [{ role: 'user', content: JSON.stringify(req.payload || {}) }],
  };

  const result = await complete(model, ctx, { apiKey: oauth.apiKey });
  if (result?.errorMessage) throw new Error(result.errorMessage);

  const text = extractAssistantText(result);
  if (!text) throw new Error('empty_llm_response');
  process.stdout.write(text);
}

main().catch((e) => {
  console.error(String(e?.message || e));
  process.exit(1);
});
