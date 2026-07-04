(function () {
  'use strict';

  // Inject shared styles dynamically to keep deployment footprint small
  function injectStyles() {
    if (document.getElementById('llm-digest-translate-styles')) return;
    const style = document.createElement('style');
    style.id = 'llm-digest-translate-styles';
    style.textContent = `
      [data-translate-ui-slot] {
        display: inline-flex;
        align-items: stretch;
        min-width: 0;
      }
      .site-context [data-translate-ui-slot] {
        align-self: stretch;
      }
      .translate-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: transparent;
        border: 1px solid var(--border);
        color: var(--fg);
        font-family: ui-monospace, "SFMono-Regular", monospace;
        font-size: 0.68rem;
        letter-spacing: 0;
        line-height: 1;
        text-decoration: none;
        white-space: nowrap;
        cursor: pointer;
        min-height: 44px;
        padding: 0 0.72rem;
        margin: 0;
        transition: border-color 0.12s ease, color 0.12s ease, background 0.12s ease;
      }
      .translate-btn:hover {
        border-color: var(--accent);
        color: var(--accent);
        background: transparent;
      }
      .site-context .translate-btn {
        height: 100%;
        width: 100%;
      }
      .translate-instruction-container {
        margin: 0.6rem 0 0;
        padding: 0.72rem 0.85rem;
        border: 1px solid var(--border);
        background: var(--brief-wash, var(--card));
        color: var(--fg);
        font-size: 0.82rem;
        line-height: 1.5;
      }
      @media (max-width: 640px) {
        .translate-btn {
          font-size: 0.66rem;
          padding: 0 0.58rem;
        }
      }
    `;
    document.head.appendChild(style);
  }


  // Curated glossary for high-value technical terms to preserve
  const CURATED_GLOSSARY = [
    "tool calling",
    "function calling",
    "retrieval-augmented generation",
    "RAG",
    "MCP",
    "evals",
    "inference",
    "latency",
    "context window",
    "context compaction",
    "agent orchestration",
    "LLM-as-judge"
  ];

  // Regex rules for glossary protection
  const ACRONYM_RE = /\b[A-Z]{2,8}\b/g;
  const MODEL_RE = /\b(?:GPT|Claude|Llama|Qwen|Gemini|Mistral|Phi|SWE)(?:-?[a-zA-Z0-9.]+)?(?:\s+[a-zA-Z0-9.]+)?\b/gi;
  const CODE_RE = /\b[a-zA-Z0-9_]+[._-][a-zA-Z0-9_.-]+\b/g;
  const URL_RE = /https?:\/\/[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}(?:\/[^\s]*)?/gi;
  const EMAIL_RE = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
  const PRICE_PERCENT_RE = /\$\d+(?:\.\d+)?%?|\b\d+(?:\.\d+)?%/g;
  const DATE_RE = /\b\d{4}-\d{2}-\d{2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:,\s+\d{4})?\b/gi;

  function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  // Glossary protection helper: replaces matches with placeholders right-to-left
  function protect(text) {
    const matches = [];
    const addMatch = (m, ruleName) => {
      const start = m.index;
      const end = start + m[0].length;
      if (matches.some(existing => (start >= existing.start && start < existing.end) || (end > existing.start && end <= existing.end))) {
        return;
      }
      matches.push({ start, end, text: m[0], rule: ruleName });
    };

    let m;
    URL_RE.lastIndex = 0;
    while ((m = URL_RE.exec(text)) !== null) addMatch(m, 'url');
    EMAIL_RE.lastIndex = 0;
    while ((m = EMAIL_RE.exec(text)) !== null) addMatch(m, 'email');

    const GLOSSARY_RE = new RegExp('\\b(' + CURATED_GLOSSARY.map(escapeRegExp).join('|') + ')\\b', 'gi');
    GLOSSARY_RE.lastIndex = 0;
    while ((m = GLOSSARY_RE.exec(text)) !== null) addMatch(m, 'glossary');

    MODEL_RE.lastIndex = 0;
    while ((m = MODEL_RE.exec(text)) !== null) addMatch(m, 'model');
    ACRONYM_RE.lastIndex = 0;
    while ((m = ACRONYM_RE.exec(text)) !== null) addMatch(m, 'acronym');
    CODE_RE.lastIndex = 0;
    while ((m = CODE_RE.exec(text)) !== null) addMatch(m, 'code');
    PRICE_PERCENT_RE.lastIndex = 0;
    while ((m = PRICE_PERCENT_RE.exec(text)) !== null) addMatch(m, 'price_percent');
    DATE_RE.lastIndex = 0;
    while ((m = DATE_RE.exec(text)) !== null) addMatch(m, 'date');

    matches.sort((a, b) => b.start - a.start);

    const placeholderMap = {};
    let protectedText = text;
    matches.forEach((match, index) => {
      const phId = matches.length - 1 - index;
      const placeholder = `__ph_${phId}__`;
      placeholderMap[phId] = match.text;
      protectedText = protectedText.slice(0, match.start) + placeholder + protectedText.slice(match.end);
    });

    return { text: protectedText, map: placeholderMap };
  }

  function restoreGlossary(translatedText, placeholderMap) {
    return translatedText.replace(/__\s*ph\s*_\s*(\d+)\s*__/gi, (match, id) => {
      const original = placeholderMap[id];
      return original !== undefined ? original : match;
    });
  }

  // Check if link represents visible URL or domain to skip translation
  function isUrlText(text, href) {
    const trimmed = text.trim();
    if (!trimmed) return false;
    if (href && trimmed === href) return true;
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) return true;
    if (/^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}(:\d+)?(\/.*)?$/.test(trimmed)) return true;
    return false;
  }

  // Check element and parents to decide whether to skip walking it
  function shouldSkipElement(el) {
    if (el.hasAttribute('data-translate-skip')) return true;
    if (el.closest('[data-translate-skip]')) return true;
    if (el.hasAttribute('data-translate-term') || el.closest('[data-translate-term]')) return true;

    const tagName = el.tagName.toLowerCase();
    const skipTags = [
      'code', 'pre', 'kbd', 'samp', 'time', 'button', 'input', 'select', 'textarea',
      'nav', 'header', 'footer', 'script', 'style', 'noscript', 'dialog'
    ];
    if (skipTags.includes(tagName)) return true;

    if (el.classList.contains('badge') ||
        el.classList.contains('art-meta') ||
        el.classList.contains('archive') ||
        el.classList.contains('controls-bar') ||
        el.classList.contains('site-chrome') ||
        el.classList.contains('site-nav-fallback') ||
        el.classList.contains('site-actions-fallback') ||
        el.classList.contains('view-mode-selector') ||
        el.classList.contains('toc') ||
        el.classList.contains('toc-links') ||
        el.classList.contains('playbook-takeaway')) {
      return true;
    }

    if (tagName === 'a') {
      const text = el.textContent || '';
      const href = el.getAttribute('href') || '';
      if (isUrlText(text, href)) return true;

      const track = el.getAttribute('data-track') || '';
      const isHumanTitle = [
        'story-link', 'weekly-link', 'storyline-link', 'topic-link',
        'foundation-link', 'story-permalink', 'story-related', 'story-covered',
        'daily-link'
      ].includes(track) || el.closest('h1, h2, h3, h4, h5, h6') !== null;


      if (!isHumanTitle) return true;
    }

    return false;
  }

  function collectTextNodes(element, list = []) {
    for (let child = element.firstChild; child; child = child.nextSibling) {
      if (child.nodeType === Node.TEXT_NODE) {
        if (child.nodeValue.trim().length > 0) {
          list.push(child);
        }
      } else if (child.nodeType === Node.ELEMENT_NODE) {
        if (!shouldSkipElement(child)) {
          collectTextNodes(child, list);
        }
      }
    }
    return list;
  }

  // Hash helper (SHA-256)
  async function computeHash(message) {
    const msgBuffer = new TextEncoder().encode(message);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  // Cache serialization and LRU eviction
  function readCache() {
    try {
      return JSON.parse(localStorage.getItem('llm_digest_translate_cache_v1')) || [];
    } catch (e) {
      return [];
    }
  }

  function saveCache(entries) {
    try {
      localStorage.setItem('llm_digest_translate_cache_v1', JSON.stringify(entries));
    } catch (e) {}
  }

  async function getCachedBlock(surface, path, targetLang, normalizedText) {
    const hash = await computeHash(surface + '|' + path + '|' + targetLang + '|' + normalizedText);
    const entries = readCache();
    const found = entries.find(e => e.key === hash);
    if (found) {
      found.lastUsed = Date.now();
      const filtered = entries.filter(e => e.key !== hash);
      filtered.push(found);
      saveCache(filtered);
      return found.value;
    }
    return null;
  }

  async function setCachedBlock(surface, path, targetLang, normalizedText, translatedTexts) {
    const hash = await computeHash(surface + '|' + path + '|' + targetLang + '|' + normalizedText);
    let entries = readCache();
    entries = entries.filter(e => e.key !== hash);
    entries.push({ key: hash, value: translatedTexts, lastUsed: Date.now() });

    while (entries.length > 100) {
      entries.shift();
    }

    while (true) {
      const serialized = JSON.stringify(entries);
      if (serialized.length > 1000000 && entries.length > 0) {
        entries.shift();
      } else {
        break;
      }
    }

    saveCache(entries);
  }

  // Telemetry client helper
  function captureEvent(event, properties = {}) {
    if (window.aiFeedPostHog && typeof window.aiFeedPostHog.capture === 'function') {
      try {
        window.aiFeedPostHog.capture(event, properties);
      } catch (e) {}
    }
  }

  // Browser assist instruction generation
  function getBrowserFamily() {
    const ua = navigator.userAgent;
    const isIOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    const isSafari = /^((?!chrome|android).)*safari/i.test(ua);
    const isFirefox = /firefox/i.test(ua);
    const isChrome = /chrome|crios|chromium/i.test(ua);
    const isMobile = /Mobi|Android/i.test(ua);

    if (isIOS || isSafari) return 'safari';
    if (isChrome && isMobile) return 'chrome-mobile';
    if (isChrome) return 'chrome';
    if (isFirefox) return 'firefox';
    return 'other';
  }

  function getBrowserAssistInstruction(targetLang) {
    const browserFamily = getBrowserFamily();

    if (browserFamily === 'safari') {
      return {
        'ko': `주소창의 'aA' 아이콘을 누르고 '한국어(으)로 번역'을 선택해주세요.`,
        'ja': `アドレスバーの「あA」アイコンをタップし、「日本語に翻訳」を選択してください。`,
        'zh-CN': `点击地址栏的“aA”图标，然后选择“翻译成中文”。`
      }[targetLang] || `Use Safari's built-in translation features.`;
    } else if (browserFamily === 'chrome-mobile') {
      return {
        'ko': `메뉴(더보기)를 누르고 '번역...'을 선택해주세요.`,
        'ja': `メニュー（3点リーダー）をタップし、「翻訳...」を選択してください。`,
        'zh-CN': `点击菜单（三点），然后选择“翻译...”。`
      }[targetLang] || `Use Chrome's built-in translation features.`;
    } else if (browserFamily === 'chrome') {
      return {
        'ko': `주소창의 번역 아이콘을 누르거나 페이지에서 마우스 오른쪽 버튼을 눌러 한국어로 번역하세요.`,
        'ja': `アドレスバーの翻訳アイコン、またはページの右クリックメニューから日本語に翻訳してください。`,
        'zh-CN': `点击地址栏的翻译图标，或右键页面并选择翻译成中文。`
      }[targetLang] || `Use Chrome's built-in translation features.`;
    } else if (browserFamily === 'firefox') {
      return {
        'ko': `주소창의 번역 아이콘을 눌러주세요.`,
        'ja': `アドレスバーの翻訳アイコンをタップしてください。`,
        'zh-CN': `点击地址栏的翻译图标。`
      }[targetLang] || `Use Firefox's built-in translation features.`;
    } else {
      return {
        'ko': `브라우저의 번역 기능을 이용해 페이지를 한국어로 번역할 수 있습니다.`,
        'ja': `ブラウザの翻訳機能を利用して、ページを日本語に翻訳できます。`,
        'zh-CN': `您可以使用浏览器自带的翻译功能将页面翻译成中文。`

      }[targetLang] || `Use your browser's translate feature for this page.`;
    }
  }

  // In-page translator session check
  async function checkChromeTranslator(targetLang) {
    if (window.Translator && typeof window.Translator.availability === 'function') {
      try {
        return await window.Translator.availability({
          sourceLanguage: 'en',
          targetLanguage: targetLang
        });
      } catch (e) {
        return 'unsupported';
      }
    }
    if (typeof window.translation === 'undefined' || typeof window.translation.canTranslate !== 'function') {
      return 'unsupported';
    }
    try {
      return await window.translation.canTranslate({
        sourceLanguage: 'en',
        targetLanguage: targetLang
      });
    } catch (e) {
      return 'unsupported';
    }
  }

  // State representation variables
  let available = false;
  let mode = null;
  let provider = null;
  let targetLanguage = null;
  let state = 'idle';
  let chromeAvailability = 'unsupported';

  let hasTrackedView = false;
  let session = null;
  const originalTextMap = new WeakMap();
  const translatedNodes = new Set();

  function isReadyInPageAvailability(value) {
    return value === 'available' || value === 'readily';
  }

  // Load preferences / detect defaults
  let pref = null;
  try {
    pref = JSON.parse(localStorage.getItem('llm_digest_translate_pref_v1'));
  } catch (e) {}

  const detectedLanguage = (function () {
    const userLangs = navigator.languages || [navigator.language || 'en'];
    if (userLangs[0] && userLangs[0].toLowerCase().startsWith('en')) {
      return null;
    }
    for (const lang of userLangs) {
      const l = lang.toLowerCase();
      if (l.startsWith('ko')) return 'ko';
      if (l.startsWith('ja')) return 'ja';
      if (l.startsWith('zh-cn') || l === 'zh') return 'zh-CN';
    }
    return null;
  })();

  targetLanguage = pref ? pref.targetLanguage : detectedLanguage;

  async function resolveProvider() {
    if (!targetLanguage) {
      available = false;
      mode = null;
      provider = null;
      state = 'idle';
      return;
    }
    state = 'checking';
    chromeAvailability = await checkChromeTranslator(targetLanguage);
    if (isReadyInPageAvailability(chromeAvailability)) {
      available = true;
      mode = 'in-page';
      provider = 'chrome-translator';
      state = 'ready';
    } else {
      const browserFamily = getBrowserFamily();
      if (['safari', 'chrome-mobile', 'chrome', 'firefox'].includes(browserFamily)) {
        available = true;
        mode = 'browser-assist';
        provider = 'browser-assist';
        state = 'ready';
      } else {
        available = false;
        mode = null;
        provider = null;
        state = 'idle';
      }
    }
  }



  // Expose public API
  const instance = {
    get available() { return available; },
    get mode() { return mode; },
    get provider() { return provider; },
    get targetLanguage() { return targetLanguage; },
    get state() { return state; },
    scan,
    translate,
    showOriginal,
    destroy,
    _test: {
      protect,
      restoreGlossary,
      isUrlText,
      shouldSkipElement,
      getBrowserAssistInstruction,
      getBrowserFamily,
      isReadyInPageAvailability,
      detectedLanguage: () => detectedLanguage
    }
  };

  window.llmDigestTranslate = instance;


  function scan() {
    const surfaceEl = document.querySelector('[data-local-translate-surface]');
    if (!surfaceEl) return;
    const surface = surfaceEl.getAttribute('data-local-translate-surface');
    if (!['daily', 'weekly', 'story'].includes(surface)) return;

    const slot = document.querySelector('[data-translate-ui-slot]');
    if (!slot) return;

    if (!available || state === 'idle' || state === 'checking') return;

    injectStyles();
    const hiddenContext = slot.closest('.site-translate-context[hidden]');
    if (hiddenContext) hiddenContext.hidden = false;

    let btn = slot.querySelector('.translate-btn');
    if (!btn) {
      btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'translate-btn';
      btn.setAttribute('aria-live', 'polite');
      slot.appendChild(btn);
      btn.addEventListener('click', () => {
        if (state === 'translated') {
          showOriginal();
        } else {
          translate();
        }
      });
    }

    // Handle view tracking
    if (!hasTrackedView) {
      hasTrackedView = true;
      captureEvent('translate_control_view', {
        surface,
        provider,
        target_language: targetLanguage,
        availability: mode === 'in-page' ? (chromeAvailability === 'readily' ? 'available' : 'downloadable') : 'unsupported'
      });
    }

    updateButtonUI(btn);
  }

  function updateButtonUI(btn) {
    if (!btn) return;
    const langNames = { 'ko': 'Korean', 'ja': 'Japanese', 'zh-CN': 'Chinese' };
    const targetName = langNames[targetLanguage] || targetLanguage;

    if (state === 'ready') {
      btn.textContent = `Translate to ${targetName}`;
    } else if (state === 'translating') {
      btn.textContent = 'Translating...';
    } else if (state === 'translated') {
      btn.textContent = 'Show original';
    } else if (state === 'assist') {
      btn.textContent = `Translation help`;
    } else if (state === 'error') {
      btn.textContent = `Retry Translate (${targetName})`;
    }
  }

  async function translate(customLang) {
    if (customLang && ['ko', 'ja', 'zh-CN'].includes(customLang)) {
      targetLanguage = customLang;
      await resolveProvider();
    }

    const surfaceEl = document.querySelector('[data-local-translate-surface]');
    const surface = surfaceEl ? surfaceEl.getAttribute('data-local-translate-surface') : 'unknown';
    const path = window.location.pathname;

    const slot = document.querySelector('[data-translate-ui-slot]');
    const btn = slot ? slot.querySelector('.translate-btn') : null;

    if (mode === 'browser-assist') {
      let instruction = document.querySelector('.translate-instruction-container');
      if (!instruction) {
        instruction = document.createElement('div');
        instruction.className = 'translate-instruction-container';
        instruction.setAttribute('aria-live', 'polite');
        const anchor = slot ? (slot.closest('.site-context') || slot) : null;
        if (anchor && anchor.parentNode) {
          anchor.insertAdjacentElement('afterend', instruction);
        }
      }
      instruction.textContent = getBrowserAssistInstruction(targetLanguage);
      instruction.style.display = '';
      state = 'assist';
      if (btn) updateButtonUI(btn);
      captureEvent('translate_browser_assist', {
        surface,
        browser_family: getBrowserFamily(),
        target_language: targetLanguage
      });
      return;
    }

    if (mode === 'in-page') {
      state = 'translating';
      if (btn) updateButtonUI(btn);

      const blocks = document.querySelectorAll('[data-translate-block]');
      captureEvent('translate_start', {
        surface,
        provider,
        target_language: targetLanguage,
        block_count: blocks.length,
        cache_hits: 0
      });

      const startTime = Date.now();
      let cacheHits = 0;

      try {
        if (!session) {
          if (provider === 'chrome-translator') {
            if (window.Translator && typeof window.Translator.create === 'function') {
              const chromeSession = await window.Translator.create({
                sourceLanguage: 'en',
                targetLanguage: targetLanguage
              });
              session = {
                async translate(text) {
                  return await chromeSession.translate(text);
                },
                destroy() {
                  if (chromeSession && typeof chromeSession.destroy === 'function') {
                    chromeSession.destroy();
                  }
                }
              };
            } else if (typeof window.translation !== 'undefined' && typeof window.translation.createTranslator === 'function') {
              const chromeSession = await window.translation.createTranslator({
                sourceLanguage: 'en',
                targetLanguage: targetLanguage
              });
              session = {
                async translate(text) {
                  return await chromeSession.translate(text);
                },
                destroy() {
                  if (chromeSession && typeof chromeSession.destroy === 'function') {
                    chromeSession.destroy();
                  }
                }
              };
            } else {
              throw new Error('translator_api_unavailable');
            }
          }
        }


        await Promise.all(Array.from(blocks).map(async (block) => {
          const textNodes = collectTextNodes(block);
          if (!textNodes.length) return;

          const blockText = textNodes.map(n => n.nodeValue).join(' ').trim().replace(/\s+/g, ' ');
          const cached = await getCachedBlock(surface, path, targetLanguage, blockText);

          if (cached && cached.length === textNodes.length) {
            cacheHits++;
            textNodes.forEach((node, idx) => {
              if (!originalTextMap.has(node)) {
                originalTextMap.set(node, node.nodeValue);
              }
              node.nodeValue = cached[idx];
              translatedNodes.add(node);
            });
            block.setAttribute('lang', targetLanguage);
          } else {
            const translatedList = await Promise.all(textNodes.map(async (node) => {
              const originalVal = node.nodeValue;
              if (!originalTextMap.has(node)) {
                originalTextMap.set(node, originalVal);
              }
              const { text: protectedText, map } = protect(originalVal);
              const translatedVal = await session.translate(protectedText);
              const restoredVal = restoreGlossary(translatedVal, map);
              node.nodeValue = restoredVal;
              translatedNodes.add(node);
              return restoredVal;
            }));
            block.setAttribute('lang', targetLanguage);
            await setCachedBlock(surface, path, targetLanguage, blockText, translatedList);
          }
        }));


        if (surfaceEl) surfaceEl.setAttribute('lang', targetLanguage);
        state = 'translated';
        if (btn) updateButtonUI(btn);

        // Save preferences
        try {
          localStorage.setItem('llm_digest_translate_pref_v1', JSON.stringify({
            targetLanguage,
          providerId: 'chrome-translator'
          }));
        } catch (e) {}

        captureEvent('translate_complete', {
          surface,
          provider,
          target_language: targetLanguage,
          block_count: blocks.length,
          duration_ms: Date.now() - startTime,
          cache_hits: cacheHits
        });
      } catch (err) {
        state = 'error';
        if (btn) updateButtonUI(btn);
        captureEvent('translate_error', {
          surface,
          provider,
          target_language: targetLanguage,
          phase: session ? 'translation' : 'session_creation',
          error_code: normalizeErrorCode(err)
        });
      }
    }
  }

  function normalizeErrorCode(err) {
    const raw = err && err.message ? String(err.message) : 'unknown';
    return raw.toLowerCase().replace(/[^a-z0-9_]+/g, '_').slice(0, 80) || 'unknown';
  }

  function showOriginal() {
    const surfaceEl = document.querySelector('[data-local-translate-surface]');
    const surface = surfaceEl ? surfaceEl.getAttribute('data-local-translate-surface') : 'unknown';

    const slot = document.querySelector('[data-translate-ui-slot]');
    const btn = slot ? slot.querySelector('.translate-btn') : null;

    if (mode === 'browser-assist') {
      const instruction = slot ? slot.querySelector('.translate-instruction-container') : null;
      if (instruction) {
        instruction.style.display = 'none';
      }
      state = 'ready';
      if (btn) updateButtonUI(btn);
      captureEvent('translate_show_original', { surface, target_language: targetLanguage });
      return;
    }

    // Restore text nodes
    translatedNodes.forEach(node => {
      if (originalTextMap.has(node)) {
        node.nodeValue = originalTextMap.get(node);
      }
    });
    translatedNodes.clear();

    // Reset lang attributes
    if (surfaceEl) surfaceEl.removeAttribute('lang');
    const blocks = document.querySelectorAll('[data-translate-block]');
    blocks.forEach(b => b.removeAttribute('lang'));

    state = 'ready';
    if (btn) updateButtonUI(btn);

    captureEvent('translate_show_original', { surface, target_language: targetLanguage });
  }

  function destroy() {
    showOriginal();
    const slot = document.querySelector('[data-translate-ui-slot]');
    if (slot) {
      slot.innerHTML = '';
    }
    if (session) {
      if (typeof session.destroy === 'function') {
        session.destroy();
      }
      session = null;
    }
    state = 'idle';
    available = false;
    mode = null;
    provider = null;
  }

  // Run initialization
  resolveProvider().then(() => {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', scan);
    } else {
      scan();
    }
  });

})();
