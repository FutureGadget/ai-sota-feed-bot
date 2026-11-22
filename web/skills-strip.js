/* Feed discovery band for the Skill Radar.
 *
 * Reads the static slice the deploy emits (web/skills-top.json), builds the
 * cards with createElement rather than innerHTML, and leaves the band hidden
 * when the artifact is missing or the lane is empty. No dependency on the feed
 * request: the feed can fail and this still renders, and vice versa. */
(function () {
  'use strict';

  // UI text comes from the page's dictionary (the global t(), written by
  // pipeline/render_home.py) where the page has one. The English fallback serves
  // pages without it; tests/test_ui_dictionary.py pins every fallback to
  // config/ui/en.json.
  function tr(key, fallback, vars) {
    var text = typeof globalThis.t === 'function' ? globalThis.t(key) : fallback;
    return vars ? text.replace(/\{(\w+)\}/g, function (match, name) { return name in vars ? vars[name] : match; }) : text;
  }

  var strip = document.getElementById('skillsStrip');
  var cards = document.getElementById('skillsStripCards');
  if (!strip || !cards) return;

  // Mobile hides the band in CSS; skip the fetch rather than load data nobody sees.
  if (window.matchMedia && window.matchMedia('(max-width: 640px)').matches) return;

  function compact(value) {
    var n = Number(value) || 0;
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
    return String(n);
  }

  function buildCard(item) {
    var link = document.createElement('a');
    link.className = 'skills-strip-card';
    link.href = '/skills/' + encodeURIComponent(item.id || '');

    var name = document.createElement('b');
    name.textContent = item.lead || item.id || '';
    link.appendChild(name);

    var reason = (item.reason || '').trim();
    if (reason) {
      var why = document.createElement('span');
      why.textContent = reason;
      link.appendChild(why);
    }

    var bits = [];
    if (item.capability_label) {
      bits.push(item.capability_label);
    }
    if (item.unique_skills) {
      bits.push(item.unique_skills === 1 ? tr('skills.countOne', '{n} skill', { n: 1 }) : tr('skills.countMany', '{n} skills', { n: item.unique_skills }));
    }
    if (item.ports) {
      bits.push(item.ports === 1 ? tr('skills.portOne', '{n} port', { n: 1 }) : tr('skills.portMany', '{n} ports', { n: item.ports }));
    }
    if (item.stars) {
      bits.push(tr('skills.stars', '{n} stars', { n: compact(item.stars) }));
    }
    if (bits.length) {
      var meta = document.createElement('span');
      meta.textContent = bits.join(' · ');
      link.appendChild(meta);
    }
    return link;
  }

  fetch('/skills-top.json', { headers: { Accept: 'application/json' } })
    .then(function (response) {
      return response.ok ? response.json() : null;
    })
    .then(function (data) {
      var items = (data && data.rising) || [];
      if (!items.length) return;
      items.slice(0, 3).forEach(function (item) {
        cards.appendChild(buildCard(item));
      });
      strip.hidden = false;
    })
    .catch(function () {
      /* Keep the band hidden; a missing radar is not an error worth surfacing. */
    });
})();
