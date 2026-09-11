// Pure reader-state rules shared by the browser and lifecycle tests.
export function initializeState(saved, items) {
  const record = (value) => value && typeof value === 'object' && !Array.isArray(value);
  if (saved?.schema === 2 && record(saved.baseline) && record(saved.seen)) return saved;
  return { schema: 2, baseline: Object.fromEntries(items.map((i) => [i.id, i.version])), seen: {} };
}

export function itemStatus(memory, item) {
  if (memory.seen[item.id] === item.version) return 'seen';
  if (memory.seen[item.id] || (memory.baseline[item.id] && memory.baseline[item.id] !== item.version)) return 'updated';
  return memory.baseline[item.id] ? 'unread' : 'new';
}

export function isFresh(item, now) {
  const limits = { daily: 1, weekly: 8, playbook: item.kind === 'lab' ? 14 : 10 };
  if (!Object.hasOwn(limits, item.section)) return true;
  const age = Math.floor(Date.parse(now) / 86400000) - Math.floor(Date.parse(item.period || item.updated_at) / 86400000);
  return Number.isFinite(age) && age >= 0 && age <= limits[item.section];
}

export function markItemOpened(memory, items, href) {
  const item = items.find((i) => i.href === href);
  if (!item) return null;
  memory.seen[item.id] = item.version;
  return item;
}
