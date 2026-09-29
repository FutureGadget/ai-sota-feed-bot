const numeric = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
const money = value => numeric(value) ? '$' + value.toLocaleString('en-US', { maximumFractionDigits: 6 }) : 'Unknown';
const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));

export function validateScenario(s) {
  for (const key of ['inputTokens', 'outputTokens', 'promptTokens', 'readPercent', 'writePercent']) {
    if (!numeric(s[key])) return 'Enter a valid non-negative number in every field.';
  }
  if (s.inputTokens < 1 || s.promptTokens < 1) return 'Input and prompt token counts must be at least 1.';
  if (s.inputTokens > 1e9 || s.outputTokens > 1e9 || s.promptTokens > 1e7) return 'Token counts exceed the supported range.';
  if (s.readPercent + s.writePercent > 100) return 'Cache reads and writes together cannot exceed 100% of input tokens.';
  return null;
}

export function estimateCost(offer, s, now = Date.now()) {
  const invalid = validateScenario(s);
  if (invalid) return { cost: null, reason: invalid };
  if (!offer) return { cost: null, reason: 'No matched provider price' };
  let rates = { ...offer.rates };
  for (const tier of offer.tiers || []) {
    if (s.promptTokens > tier.min_prompt_tokens) rates = { ...tier.rates };
  }
  const fail = reason => ({ cost: null, reason, rates });
  const checked = Date.parse(offer.checked_at);
  if (!Number.isFinite(checked) || now - checked > 86400000) return fail('Price is over 24 hours old');
  if (!numeric(offer.context_length)) return fail('Context limit is unknown');
  if (s.promptTokens > offer.context_length) return fail('Prompt exceeds this endpoint’s context limit');
  if (offer.request_usd > 0) return fail('Additional per-request fee');
  const read = s.readPercent / 100;
  const write = s.writePercent / 100;
  const input = Math.max(0, 1 - read - write);
  const writeKey = s.writeDuration === '1h' ? 'cache_write_1h' : 'cache_write';
  if (write > 0 && !numeric(rates[writeKey])) return fail('Cache-write rate is unknown');
  if (write > 0 && offer.write_basis !== 'replacement') return fail('Cache-write basis is unverified');
  const terms = [
    [s.inputTokens * input, rates.input, 'Input rate'],
    [s.inputTokens * read, rates.cache_read, 'Cache-read rate'],
    [s.inputTokens * write, rates[writeKey], 'Cache-write rate'],
    [s.outputTokens, rates.output, 'Output rate'],
  ];
  let cost = 0;
  for (const [tokens, rate, label] of terms) {
    if (tokens <= 1e-8) continue;
    if (!numeric(rate)) return fail(`${label} is unknown`);
    cost += tokens * rate / 1e6;
  }
  return { cost, rates, reason: null };
}

export function pareto(points) {
  return points.filter(p => !points.some(q => q.cost <= p.cost && q.score >= p.score && (q.cost < p.cost || q.score > p.score)));
}

export function compareModels(models, metric, scenario, now = Date.now()) {
  const groups = new Map();
  for (const model of models) {
    const key = model.url_slug;
    if (!key) continue;
    const current = groups.get(key);
    const score = numeric(model[metric]) ? model[metric] : -1;
    const previous = current && numeric(current[metric]) ? current[metric] : -1;
    if (!current || score > previous) groups.set(key, model);
  }
  const rows = [...groups.values()].map(model => {
    const estimate = estimateCost(model.pricing, scenario, now);
    const score = numeric(model[metric]) ? model[metric] : null;
    return { model, score, cost: estimate.cost, rates: estimate.rates, reason: score === null ? 'Awaiting benchmark score' : estimate.reason };
  });
  const points = rows.filter(p => p.score !== null && p.cost !== null);
  const frontier = new Set(pareto(points));
  for (const row of rows) row.frontier = frontier.has(row);
  return rows.sort((a, b) => (b.score ?? -1) - (a.score ?? -1) || (a.cost ?? Infinity) - (b.cost ?? Infinity));
}

function startComparison(data) {
  const $ = id => document.getElementById(id);
  const form = $('scenario');
  let rows = [], selected = null, frontierOnly = false;
  const modelName = row => row.model.display_name || row.model.name;
  const metricLabel = () => $('metric').selectedOptions[0].textContent;
  function scenario() {
    const value = { writeDuration: $('writeDuration').value };
    for (const key of ['inputTokens', 'outputTokens', 'promptTokens', 'readPercent', 'writePercent']) value[key] = $(key).value === '' ? NaN : Number($(key).value);
    return value;
  }
  function selectModel(slug) {
    const row = rows.find(r => r.model.url_slug === slug);
    if (!row) return;
    selected = slug;
    document.querySelectorAll('.point').forEach(p => p.classList.toggle('selected', p.dataset.slug === slug));
    const p = row.model.pricing;
    const effort = row.model.variant_label || 'standard';
    $('selection').innerHTML = `<strong><a href="/models/${esc(slug)}">${esc(modelName(row))}</a></strong> · ${esc(effort)} effort
      <p>${row.score === null ? 'Awaiting benchmark score' : `${row.score.toFixed(1)} ${esc(metricLabel())}`} · ${row.cost === null ? esc(row.reason) : `${money(row.cost)} estimated spend`}${row.frontier ? ' · <span class="mc-badge">ON FRONTIER</span>' : ''}</p>
      ${p ? `<p>${esc(p.provider)} (${esc(p.tag)}) · ${numeric(p.context_length) ? p.context_length.toLocaleString() : 'Unknown'} context tokens · <a href="${esc(p.source_url)}">OpenRouter source</a> · Checked ${esc(new Date(p.checked_at).toLocaleString())}${p.refresh_error ? ' (last refresh failed)' : ''}.</p>` : '<p>No matched provider offer yet.</p>'}`;
  }
  function renderTable() {
    const query = $('search').value.trim().toLowerCase();
    const shown = rows.filter(r => (!frontierOnly || r.frontier) && `${modelName(r)} ${r.model.pricing?.provider || ''}`.toLowerCase().includes(query));
    $('prices').innerHTML = shown.length ? shown.map(r => {
      const p = r.model.pricing;
      const rates = r.rates || p?.rates || {};
      const rate = key => key.startsWith('cache_write') && numeric(rates[key]) && p?.write_basis !== 'replacement' ? 'Unverified' : money(rates[key]);
      return `<tr><td><button type="button" data-inspect="${esc(r.model.url_slug)}">${esc(modelName(r))}</button><small>${esc(p?.provider || 'No provider price')} · ${esc(r.model.variant_label || 'standard')}${r.frontier ? ' · <span class="mc-badge">FRONTIER</span>' : ''}</small></td>
        <td>${r.score === null ? 'Pending' : r.score.toFixed(1)}</td><td>${r.cost === null ? 'Unavailable' : money(r.cost)}${r.reason ? `<small>${esc(r.reason)}</small>` : ''}</td>
        <td>${rate('input')}</td><td>${rate('output')}</td><td>${rate('cache_read')}</td><td>${rate('cache_write')}<small>${esc(p?.write_ttl || 'default')}</small></td><td>${rate('cache_write_1h')}</td></tr>`;
    }).join('') : '<tr><td colspan="8">No models match these filters.</td></tr>';
    $('prices').querySelectorAll('[data-inspect]').forEach(button => button.addEventListener('click', () => { selectModel(button.dataset.inspect); $('selection').scrollIntoView({ block: 'nearest' }); }));
  }
  function renderChart() {
    const points = rows.filter(p => p.score !== null && p.cost !== null);
    if (!points.length) { $('chart').innerHTML = '<p>No models have all the rates and scores needed for this scenario. Try an uncached workload or a shorter prompt.</p>'; return; }
    const width = Math.max(340, Math.min(1100, $('chart').clientWidth));
    const height = width < 600 ? 380 : 440;
    const left = 48, right = width - 22, top = 26, bottom = height - 56;
    const maxCost = Math.max(.01, ...points.map(p => p.cost)) * 1.18;
    const maxScore = Math.ceil(Math.max(...points.map(p => p.score)) / 10) * 10 || 10;
    // log1p keeps truly free offers at zero without inventing a positive price.
    const x = cost => left + Math.log1p(cost) / Math.log1p(maxCost) * (right - left);
    const y = score => bottom - score / maxScore * (bottom - top);
    const ticks = [0, .01, .1, .5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 5000, 10000, 100000, 1000000];
    let lastX = -Infinity;
    const xTicks = ticks.filter(t => { if (t > maxCost || x(t) - lastX < 48) return false; lastX = x(t); return true; });
    const scoreStep = Math.max(10, Math.ceil(maxScore / 60) * 10);
    const grid = xTicks.map(t => `<line class="gridline" x1="${x(t)}" x2="${x(t)}" y1="${top}" y2="${bottom}"/><text class="axis-label" x="${x(t)}" y="${bottom + 22}" text-anchor="middle">${money(t)}</text>`).join('') + Array.from({ length: Math.floor(maxScore / scoreStep) + 1 }, (_, i) => {
      const score = scoreStep * i;
      return `<line class="gridline" x1="${left}" x2="${right}" y1="${y(score)}" y2="${y(score)}"/><text class="axis-label" x="${left - 9}" y="${y(score) + 4}" text-anchor="end">${score.toFixed(0)}</text>`;
    }).join('');
    const frontier = points.filter(p => p.frontier).sort((a, b) => a.cost - b.cost);
    const path = frontier.map((p, i) => `${i ? 'L' : 'M'}${x(p.cost)},${y(p.score)}`).join(' ');
    const circles = [...points].sort((a, b) => Number(a.frontier) - Number(b.frontier)).map(p => {
      const label = `${modelName(p)}, ${p.model.variant_label || 'standard'} effort, score ${p.score.toFixed(1)}, ${money(p.cost)}${p.frontier ? ', on frontier' : ''}`;
      return `<circle class="point${p.frontier ? ' frontier' : ''}${p.model.url_slug === selected ? ' selected' : ''}" cx="${x(p.cost)}" cy="${y(p.score)}" r="${p.frontier ? 6 : 4.5}" tabindex="0" role="button" aria-label="${esc(label)}" data-slug="${esc(p.model.url_slug)}"><title>${esc(label)}</title></circle>`;
    }).join('');
    const occupied = [];
    const labels = [...frontier].sort((a, b) => b.score - a.score).slice(0, width < 600 ? 3 : 7).map(p => {
      const name = modelName(p), labelWidth = Math.min(name.length * 6.8, width / 2);
      const px = Math.max(left, Math.min(right - labelWidth, x(p.cost) + 9));
      let py = y(p.score) - 12;
      while (occupied.some(r => px < r.x + r.width && px + labelWidth > r.x && Math.abs(py - r.y) < 18)) py += 20;
      occupied.push({ x: px, y: py, width: labelWidth });
      return `<text class="point-label" x="${px}" y="${py}">${esc(name)}</text>`;
    }).join('');
    $('chart').innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="group" aria-labelledby="plotTitle plotDescription"><title id="plotTitle">${esc(metricLabel())} versus estimated spend</title><desc id="plotDescription">Green points form the Pareto frontier. Select a point to inspect it. The complete prices and values are in the table below.</desc>${grid}<path class="frontier-line" d="${path}"/>${circles}${labels}<text class="axis-label" x="${left}" y="14">${esc(metricLabel())} ↑</text><text class="axis-label" x="${width / 2}" y="${height - 6}" text-anchor="middle">Estimated USD · compressed cost axis →</text></svg>`;
    $('chart').querySelectorAll('[data-slug]').forEach(point => {
      point.addEventListener('click', () => selectModel(point.dataset.slug));
      point.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectModel(point.dataset.slug); } });
    });
  }
  function render() {
    const s = scenario(), error = validateScenario(s);
    $('validation').hidden = !error;
    $('validation').textContent = error || '';
    if (error) { rows = []; $('chart').innerHTML = ''; $('prices').innerHTML = ''; $('coverage').textContent = ''; $('selection').textContent = 'Correct the assumptions above to compare models.'; return; }
    rows = compareModels(data.models || [], $('metric').value, s);
    $('assumptions').textContent = `${s.inputTokens.toLocaleString()} input + ${s.outputTokens.toLocaleString()} output tokens; ${s.readPercent}% cache reads, ${s.writePercent}% cache writes, ${100 - s.readPercent - s.writePercent}% uncached. Prices below use the ${s.promptTokens.toLocaleString()}-token prompt tier.`;
    $('chartTitle').textContent = $('metric').value === 'aa_coding_index' ? 'Cost vs. coding capability' : 'Cost vs. intelligence';
    const paired = rows.filter(r => r.cost !== null && r.score !== null);
    const pending = rows.filter(r => r.score === null).length;
    $('coverage').textContent = `${paired.length} comparable models · ${paired.filter(r => r.frontier).length} on the frontier · ${pending} awaiting scores · ${rows.length - pending - paired.length} lack a usable price for this scenario. All tracked models remain in the table.`;
    if (!selected || !rows.some(r => r.model.url_slug === selected)) selected = (paired.find(r => r.frontier) || rows[0])?.model.url_slug;
    renderChart(); renderTable(); selectModel(selected);
  }
  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('input', event => {
    if (event.target.id === 'preset' && event.target.value !== 'custom') {
      $('readPercent').value = event.target.value === 'warm' ? 90 : 0;
      $('writePercent').value = event.target.value === 'warm' ? 10 : 0;
    } else if (['readPercent', 'writePercent'].includes(event.target.id)) $('preset').value = 'custom';
    render();
  });
  $('search').addEventListener('input', renderTable);
  $('frontierOnly').addEventListener('click', () => { frontierOnly = !frontierOnly; $('frontierOnly').setAttribute('aria-pressed', String(frontierOnly)); renderTable(); });
  const source = data.sources?.openrouter;
  $('freshness').textContent = `OpenRouter catalog checked: ${source?.catalog_checked_at ? new Date(source.catalog_checked_at).toLocaleString() : 'not yet available'}. Benchmarks collected: ${data.generated_at ? new Date(data.generated_at).toLocaleString() : 'unknown'}. Endpoint check times appear when you select a model.`;
  let resize;
  window.addEventListener('resize', () => { clearTimeout(resize); resize = setTimeout(() => { if (!validateScenario(scenario())) renderChart(); }, 120); });
  render();
}

if (typeof document !== 'undefined') {
  document.getElementById('themeToggle').addEventListener('click', () => {
    const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme; localStorage.setItem('theme', theme);
  });
  fetch('/models-data.json').then(response => { if (!response.ok) throw new Error('Prices unavailable'); return response.json(); }).then(startComparison).catch(() => {
    document.getElementById('assumptions').textContent = 'Model data could not be loaded. Reload the page to retry.';
  });
}
