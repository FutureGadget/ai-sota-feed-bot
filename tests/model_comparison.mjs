import assert from 'node:assert/strict';
import { estimateCost, compareModels, pareto, validateScenario } from '../web/model-comparison.mjs';

const now = Date.parse('2026-09-29T12:00:00Z');
const offer = { rates: { input: 2, output: 10, cache_read: .2, cache_write: 2.5, cache_write_1h: 4 },
  checked_at: '2026-09-29T12:00:00Z', write_basis: 'replacement', context_length: 1000000, tiers: [] };
const warm = { inputTokens: 1000000, outputTokens: 250000, readPercent: 90, writePercent: 10, writeDuration: 'default', promptTokens: 32000 };
assert.equal(estimateCost(offer, warm, now).cost, 2.93);
assert.equal(estimateCost(offer, { ...warm, outputTokens: 0 }, now).cost, .43);
assert.ok(Math.abs(estimateCost(offer, { ...warm, outputTokens: 0, writeDuration: '1h' }, now).cost - .58) < 1e-10);
const cold = { ...warm, readPercent: 0, writePercent: 0 };
assert.equal(estimateCost(offer, cold, now).cost, 4.5);
assert.equal(estimateCost({ ...offer, rates: { input: 0, output: 0 } }, cold, now).cost, 0);
assert.equal(estimateCost({ ...offer, rates: { input: 2, output: 10 } }, warm, now).cost, null);
assert.equal(estimateCost({ ...offer, write_basis: 'unverified' }, warm, now).cost, null);
assert.equal(estimateCost({ ...offer, write_basis: 'unverified' }, cold, now).cost, 4.5);
assert.equal(estimateCost(offer, warm, now + 86400001).cost, null);
assert.equal(estimateCost(offer, { ...warm, promptTokens: 1000001 }, now).cost, null);
assert.ok(validateScenario({ ...warm, readPercent: 91 }));
assert.ok(validateScenario({ ...warm, inputTokens: NaN }));
const tiered = { ...offer, tiers: [{ min_prompt_tokens: 272000, rates: { ...offer.rates, input: 4, output: 15 } }] };
assert.equal(estimateCost(tiered, { ...cold, promptTokens: 272000 }, now).cost, 4.5);
assert.equal(estimateCost(tiered, { ...cold, promptTokens: 272001 }, now).cost, 7.75);
assert.deepEqual(pareto([{ cost: 0, score: 10 }, { cost: 0, score: 9 }, { cost: 1, score: 10 }, { cost: 2, score: 20 }, { cost: 2, score: 20 }]), [{ cost: 0, score: 10 }, { cost: 2, score: 20 }, { cost: 2, score: 20 }]);
const models = [
  { url_slug: 'a', aa_intelligence_index: 50, aa_coding_index: 20, variant_label: 'high', pricing: offer },
  { url_slug: 'a', aa_intelligence_index: 40, aa_coding_index: 30, variant_label: 'low', pricing: offer },
  { url_slug: 'b', aa_intelligence_index: 49, aa_coding_index: 40, pricing: { ...offer, rates: { ...offer.rates, input: 1, output: 1, cache_read: 20 } } },
  { url_slug: 'new', pricing: offer },
];
assert.equal(compareModels(models, 'aa_intelligence_index', warm, now).find(r => r.model.url_slug === 'a').model.variant_label, 'high');
assert.equal(compareModels(models, 'aa_coding_index', warm, now).find(r => r.model.url_slug === 'a').model.variant_label, 'low');
assert.equal(compareModels(models, 'aa_intelligence_index', warm, now).filter(r => r.frontier).length, 1);
assert.equal(compareModels(models, 'aa_intelligence_index', cold, now).filter(r => r.frontier).length, 2);
assert.equal(compareModels(models, 'aa_intelligence_index', cold, now).find(r => r.model.url_slug === 'new').score, null);
console.log('Model comparison: cache arithmetic, tiers, freshness, zero, unknown rates, metric/effort pairing and changing frontiers pass.');
