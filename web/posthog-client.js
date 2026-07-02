(function () {
  var pending = [];
  var enabled = false;
  var disabled = false;

  function randomId(prefix) {
    if (window.crypto && window.crypto.randomUUID) return prefix + '_' + window.crypto.randomUUID();
    return prefix + '_' + Math.random().toString(36).slice(2) + '_' + Date.now();
  }

  function getAnonUserId() {
    var key = 'ai_feed_anon_user_id';
    try {
      var v = localStorage.getItem(key);
      if (!v) {
        v = randomId('anon');
        localStorage.setItem(key, v);
      }
      return v;
    } catch (e) {
      return randomId('anon');
    }
  }

  function capture(event, properties) {
    if (!event) return;
    if (enabled && window.posthog && window.posthog.capture) {
      try {
        window.posthog.capture(event, properties || {});
      } catch (e) {
        console.debug('posthog_capture_failed', e);
      }
      return;
    }
    if (!disabled) pending.push([event, properties || {}]);
  }

  function flushPending() {
    var events = pending;
    pending = [];
    for (var i = 0; i < events.length; i += 1) {
      capture(events[i][0], events[i][1]);
    }
  }

  function installPostHogStub() {
    (function (document, posthog) {
      if (posthog.__SV) return;
      window.posthog = posthog;
      posthog._i = posthog._i || [];
      posthog.__SV = 1;
      posthog.init = function (apiKey, options, name) {
        var target = name ? (posthog[name] = []) : posthog;
        target.people = target.people || [];
        var methods = [
          'capture',
          'identify',
          'alias',
          'people.set',
          'people.set_once',
          'register',
          'register_once',
          'unregister',
          'reset',
          'isFeatureEnabled',
        ];
        var factory = function (method) {
          return function () {
            target.push([method].concat(Array.prototype.slice.call(arguments, 0)));
          };
        };
        for (var i = 0; i < methods.length; i += 1) {
          var parts = methods[i].split('.');
          if (parts.length === 2) {
            target[parts[0]][parts[1]] = factory(methods[i]);
          } else {
            target[methods[i]] = factory(methods[i]);
          }
        }
        posthog._i.push([apiKey, options, name]);
      };
    })(document, window.posthog || []);
  }

  function loadPostHogScript(host) {
    if (document.getElementById('posthog-array-js')) return;
    var script = document.createElement('script');
    script.id = 'posthog-array-js';
    script.async = true;
    script.crossOrigin = 'anonymous';
    script.src = (host || 'https://us.i.posthog.com').replace('.i.posthog.com', '-assets.i.posthog.com') + '/static/array.js';
    script.onerror = function () { console.debug('posthog_loader_failed'); };
    document.head.appendChild(script);
  }

  async function init() {
    try {
      var res = await fetch('/api/client-config', { headers: { accept: 'application/json' } });
      if (!res.ok) {
        disabled = true;
        pending = [];
        return;
      }
      var cfg = await res.json();
      var ph = (cfg && cfg.posthog) || {};
      if (!ph.enabled || !ph.project_api_key) {
        disabled = true;
        pending = [];
        return;
      }

      installPostHogStub();

      window.posthog.init(ph.project_api_key, {
        api_host: ph.host || 'https://us.i.posthog.com',
        person_profiles: 'identified_only',
        autocapture: false,
        capture_pageview: false,
        capture_pageleave: true,
        persistence: 'localStorage+cookie',
        loaded: function (sdk) {
          var anon = getAnonUserId();
          sdk.identify(anon);
          sdk.capture('page_view', {
            path: window.location.pathname,
            referrer: document.referrer || null,
          });
          window.__posthogEnabled = true;
          enabled = true;
          flushPending();
        },
      });

      loadPostHogScript(ph.host || 'https://us.i.posthog.com');
    } catch (e) {
      disabled = true;
      pending = [];
      console.debug('posthog_init_failed', e);
    }
  }

  window.aiFeedPostHog = {
    capture: capture,
    getAnonUserId: getAnonUserId,
    init: init,
  };

  init();
})();
