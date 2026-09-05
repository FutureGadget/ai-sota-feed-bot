import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';


function visibilityPredicate(filename) {
  const source = fs.readFileSync(filename, 'utf8');
  const match = source.match(
    /function skillLabMeetsVisibility\(entries, threshold\) \{\s*return ([\s\S]*?);\s*\}/
  );
  assert.ok(match, `${filename} exposes the shared visibility predicate`);
  return new Function('entries', 'threshold', `return ${match[1]};`);
}

for (const filename of ['web/playbook.html', 'web/playbook-lab.html', 'web/index.html']) {
  test(`${filename} counts a Lab view only at the declared ratio`, () => {
    const visible = visibilityPredicate(filename);
    assert.equal(visible([{ isIntersecting: true, intersectionRatio: 0.066 }], 0.35), false);
    assert.equal(visible([{ isIntersecting: true, intersectionRatio: 0.35 }], 0.35), true);
    assert.equal(visible([{ isIntersecting: false, intersectionRatio: 1 }], 0.35), false);
  });
}
