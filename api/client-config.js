export default async function handler(request) {
  if (request.method !== 'GET') {
    return Response.json(
      { error: 'method_not_allowed' },
      {
        status: 405,
        headers: { Allow: 'GET' }
      }
    );
  }

  const defaultPostHogKey = 'phc_frYL2od402eAmmxvKFZXbb4pbLNCZpI82mPW9VVAOHu';
  const key = String(process.env.POSTHOG_PROJECT_API_KEY || defaultPostHogKey).trim();
  // Reverse-proxied through the llm-digest-proxy-worker Cloudflare Worker
  // (assets.llm-digest.com) so ingestion/asset requests are first-party.
  const host = String(process.env.POSTHOG_HOST || 'https://assets.llm-digest.com').trim();
  // ui_host must stay PostHog's real domain (never the proxy) so in-app
  // features like the toolbar link back to the actual PostHog UI.
  const uiHost = String(process.env.POSTHOG_UI_HOST || 'https://us.posthog.com').trim();
  const enabledFlag = String(process.env.POSTHOG_ENABLED || '1').trim().toLowerCase();
  const enabled = !['0', 'false', 'off'].includes(enabledFlag) && !!key;

  // Optional external email-digest signup page (e.g. an RSS-to-email form); the
  // subscribe menu shows an outbound email link only when this is configured.
  const emailSignup = String(process.env.DIGEST_EMAIL_SIGNUP_URL || '').trim();
  // In-page subscribe (POST /api/subscribe → Resend contacts). Resend contacts
  // are global, so registration needs only the API key — no audience/segment id
  // (a segment id is a send-time concern). Enabled when the key is present.
  const emailSubscribeEnabled = !!String(process.env.EMAIL_API_KEY || '').trim();

  return Response.json({
    posthog: {
      enabled,
      host,
      ui_host: uiHost,
      defaults: '2026-05-30',
      project_api_key: enabled ? key : null,
    },
    digest: {
      email_signup_url: /^https:\/\//.test(emailSignup) ? emailSignup : null,
      email_subscribe_enabled: emailSubscribeEnabled,
    },
  });
}
