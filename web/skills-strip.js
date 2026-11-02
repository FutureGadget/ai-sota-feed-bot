/* Feed discovery band for the Skill Radar.
 *
 * Reads the static slice the deploy emits (web/skills-top.json), builds the
 * cards with createElement rather than innerHTML, and leaves the band hidden
 * when the artifact is missing or the lane is empty. No dependency on the feed
 * request: the feed can fail and this still renders, and vice versa. */
(function () {
  'use strict';

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
      bits.push(item.unique_skills + (item.unique_skills === 1 ? ' skill' : ' skills'));
    }
    if (item.ports) {
      bits.push(item.ports + (item.ports === 1 ? ' port' : ' ports'));
    }
    if (item.stars) {
      bits.push(compact(item.stars) + ' stars');
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
