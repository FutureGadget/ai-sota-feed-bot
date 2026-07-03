const API_HOST = "us.i.posthog.com"
const ASSET_HOST = "us-assets.i.posthog.com"
const ALLOWED_ORIGINS = new Set([
  "https://www.llm-digest.com",
  "https://llm-digest.com",
])
const ALLOWED_ORIGIN_PATTERN =
  /^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/

async function handleRequest(request, ctx) {
  const url = new URL(request.url)
  const pathname = url.pathname
  const search = url.search
  const pathWithParams = pathname + search

  if (request.method === "OPTIONS") {
    return preflightResponse(request)
  }

  if (pathname.startsWith("/static/") || pathname.startsWith("/array/")) {
    return retrieveAsset(request, pathWithParams, ctx)
  } else {
    return forwardRequest(request, pathWithParams)
  }
}

function allowedOrigin(request) {
  const origin = request.headers.get("Origin") || ""
  if (ALLOWED_ORIGINS.has(origin) || ALLOWED_ORIGIN_PATTERN.test(origin)) {
    return origin
  }
  return ""
}

function corsHeaders(request) {
  const origin = allowedOrigin(request)
  const headers = new Headers({
    "Access-Control-Allow-Methods": "GET,HEAD,POST,OPTIONS",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  })

  const requestHeaders = request.headers.get("Access-Control-Request-Headers")
  headers.set(
    "Access-Control-Allow-Headers",
    requestHeaders || "Content-Type, Authorization, X-Requested-With"
  )

  if (origin) {
    headers.set("Access-Control-Allow-Origin", origin)
    headers.set("Access-Control-Allow-Credentials", "true")
  }

  return headers
}

function withCors(response, request) {
  const headers = new Headers(response.headers)
  for (const [key, value] of corsHeaders(request)) {
    headers.set(key, value)
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  })
}

function preflightResponse(request) {
  return new Response(null, {
    status: 204,
    headers: corsHeaders(request),
  })
}

async function retrieveAsset(request, pathname, ctx) {
  let response = await caches.default.match(request)
  if (!response) {
    response = await fetch(`https://${ASSET_HOST}${pathname}`)
    ctx.waitUntil(caches.default.put(request, response.clone()))
  }
  return withCors(response, request)
}

async function forwardRequest(request, pathWithSearch) {
  const ip = request.headers.get("CF-Connecting-IP") || ""
  const originHeaders = new Headers(request.headers)
  originHeaders.delete("cookie")
  originHeaders.set("X-Forwarded-For", ip)

  const originRequest = new Request(`https://${API_HOST}${pathWithSearch}`, {
    method: request.method,
    headers: originHeaders,
    body: request.method !== "GET" && request.method !== "HEAD" ? await request.arrayBuffer() : null,
    redirect: request.redirect
  })

  const response = await fetch(originRequest)
  return withCors(response, request)
}

export default {
  async fetch(request, env, ctx) {
    return handleRequest(request, ctx);
  }
};
