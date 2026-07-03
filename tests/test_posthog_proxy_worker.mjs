import assert from "node:assert/strict"

const worker = await import("../infra/llm-digest-proxy-worker/src/index.js")

function makeCtx() {
  const waits = []
  return {
    waits,
    waitUntil(promise) {
      waits.push(promise)
    },
  }
}

async function testPreflightCors() {
  const res = await worker.default.fetch(
    new Request("https://assets.llm-digest.com/e/", {
      method: "OPTIONS",
      headers: {
        Origin: "https://www.llm-digest.com",
        "Access-Control-Request-Headers": "content-type,x-posthog-test",
      },
    }),
    {},
    makeCtx()
  )

  assert.equal(res.status, 204)
  assert.equal(res.headers.get("Access-Control-Allow-Origin"), "https://www.llm-digest.com")
  assert.equal(res.headers.get("Access-Control-Allow-Credentials"), "true")
  assert.equal(res.headers.get("Access-Control-Allow-Headers"), "content-type,x-posthog-test")
}

async function testCachedAssetCors() {
  globalThis.caches = {
    default: {
      async match() {
        return new Response("console.log('posthog')", {
          headers: { "Content-Type": "text/javascript" },
        })
      },
      async put() {
        throw new Error("cached response should not be written")
      },
    },
  }

  const res = await worker.default.fetch(
    new Request("https://assets.llm-digest.com/array/phc_key/config.js", {
      headers: { Origin: "https://www.llm-digest.com" },
    }),
    {},
    makeCtx()
  )

  assert.equal(res.status, 200)
  assert.equal(res.headers.get("Access-Control-Allow-Origin"), "https://www.llm-digest.com")
  assert.equal(res.headers.get("Content-Type"), "text/javascript")
  assert.equal(await res.text(), "console.log('posthog')")
}

async function testForwardRequestCorsAndHeaders() {
  let forwardedRequest
  globalThis.caches = {
    default: {
      async match() {
        return null
      },
      async put() {},
    },
  }
  globalThis.fetch = async (request) => {
    forwardedRequest = request
    return new Response('{"status":"Ok"}', {
      headers: { "Content-Type": "application/json" },
    })
  }

  const res = await worker.default.fetch(
    new Request("https://assets.llm-digest.com/e/", {
      method: "POST",
      headers: {
        Origin: "https://www.llm-digest.com",
        Cookie: "session=private",
        "CF-Connecting-IP": "203.0.113.5",
        "Content-Type": "application/json",
      },
      body: "{}",
    }),
    {},
    makeCtx()
  )

  assert.equal(forwardedRequest.url, "https://us.i.posthog.com/e/")
  assert.equal(forwardedRequest.headers.get("Cookie"), null)
  assert.equal(forwardedRequest.headers.get("X-Forwarded-For"), "203.0.113.5")
  assert.equal(res.headers.get("Access-Control-Allow-Origin"), "https://www.llm-digest.com")
}

await testPreflightCors()
await testCachedAssetCors()
await testForwardRequestCorsAndHeaders()
