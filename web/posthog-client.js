(function () {
  var pending = [];
  var enabled = false;
  var disabled = false;
  var scrollDepthStarted = false;

  function isLocalHost() {
    return /^(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])$/.test(window.location.hostname);
  }

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

  function scrollPercent() {
    var doc = document.documentElement;
    var body = document.body;
    var scrollTop = window.pageYOffset || doc.scrollTop || body.scrollTop || 0;
    var viewport = window.innerHeight || doc.clientHeight || 0;
    var height = Math.max(
      body ? body.scrollHeight : 0,
      body ? body.offsetHeight : 0,
      doc ? doc.clientHeight : 0,
      doc ? doc.scrollHeight : 0,
      doc ? doc.offsetHeight : 0
    );
    var scrollable = Math.max(0, height - viewport);
    if (!scrollable) return 100;
    return Math.max(0, Math.min(100, Math.round(((scrollTop + viewport) / height) * 100)));
  }

  function startScrollDepthTracking() {
    if (scrollDepthStarted) return;
    scrollDepthStarted = true;

    var thresholds = [25, 50, 75, 90, 100];
    var seen = {};
    var ticking = false;
    var maxPercent = 0;

    function check() {
      ticking = false;
      maxPercent = Math.max(maxPercent, scrollPercent());
      for (var i = 0; i < thresholds.length; i += 1) {
        var threshold = thresholds[i];
        if (seen[threshold] || maxPercent < threshold) continue;
        seen[threshold] = true;
        capture('scroll_depth', {
          path: window.location.pathname,
          percent: threshold,
          max_percent: maxPercent,
        });
      }
    }

    function schedule() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(check);
    }

    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule, { passive: true });
    window.addEventListener('pagehide', check);
    schedule();
  }

  function captureLegacyPageView(sdk) {
    try {
      sdk.capture('page_view', {
        path: window.location.pathname,
        referrer: document.referrer || null,
      });
    } catch (e) {
      console.debug('posthog_legacy_page_view_failed', e);
    }
  }

  function installPostHogSnippet() {
    !(function (t, e) {
      var o, n, p, r;
      e.__SV ||
        ((window.posthog = e),
        (e._i = []),
        (e.init = function (i, s, a) {
          function g(t, e) {
            var o = e.split(".");
            (2 == o.length && ((t = t[o[0]]), (e = o[1])),
              (t[e] = function () {
                t.push([e].concat(Array.prototype.slice.call(arguments, 0)));
              }));
          }
          (((p = t.createElement("script")).type = "text/javascript"),
            (p.crossOrigin = "anonymous"),
            (p.async = !0),
            (p.src =
              s.api_host.replace(".i.posthog.com", "-assets.i.posthog.com") + "/static/array.js"),
            (r = t.getElementsByTagName("script")[0]).parentNode.insertBefore(p, r));
          var u = e;
          for (
            void 0 !== a ? (u = e[a] = []) : (a = "posthog"),
              u.people = u.people || [],
              u.toString = function (t) {
                var e = "posthog";
                return ("posthog" !== a && (e += "." + a), t || (e += " (stub)"), e);
              },
              u.people.toString = function () {
                return u.toString(1) + ".people (stub)";
              },
              o =
                "init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagResult isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey getNextSurveyStep identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty createPersonProfile opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing debug".split(
                  " ",
                ),
              n = 0;
            n < o.length;
            n++
          )
            g(u, o[n]);
          e._i.push([i, s, a]);
        }),
        (e.__SV = 1));
    })(document, window.posthog || []);
  }

  async function init() {
    try {
      if (isLocalHost()) {
        disabled = true;
        pending = [];
        return;
      }

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

      installPostHogSnippet();

      window.posthog.init(ph.project_api_key, {
        api_host: ph.host || 'https://assets.llm-digest.com',
        ui_host: ph.ui_host || 'https://us.posthog.com',
        defaults: ph.defaults || '2026-05-30',
        person_profiles: 'identified_only',
        autocapture: false,
        // Emit the standard `$pageview` (SPA-aware) so PostHog Web Analytics
        // counts visitors/sessions/pages. The loaded callback also emits the
        // legacy `page_view` event so existing PostHog insights stay live.
        capture_pageview: 'history_change',
        capture_pageleave: true,
        persistence: 'localStorage+cookie',
        loaded: function (sdk) {
          var anon = getAnonUserId();
          sdk.identify(anon);
          window.__posthogEnabled = true;
          enabled = true;
          captureLegacyPageView(sdk);
          startScrollDepthTracking();
          flushPending();
        },
      });
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
    startScrollDepthTracking: startScrollDepthTracking,
  };

  init();
})();
