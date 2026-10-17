// Render a storyboard to MP4: seek the deterministic player frame by frame in
// headless Chromium and pipe PNGs into ffmpeg.
//   node video/render.mjs <storyboard.json> <out.mp4> [--audio narration.wav] [--fps 30] [--scale 1] [--frame <t> <out.png>]
// Needs the `playwright` package (npm i -D playwright) and a Chromium build.
import { createRequire } from "node:module";
import { spawn } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
function loadPlaywright() {
  for (const spec of ["playwright", process.env.PLAYWRIGHT_MODULE].filter(Boolean)) {
    try { return require(spec); } catch {}
  }
  console.error("video_render_skipped reason=missing_playwright");
  process.exit(3);
}

const args = process.argv.slice(2);
const flag = (n, d) => { const i = args.indexOf(n); return i < 0 ? d : args[i + 1]; };
const [sbPath, outPath] = args.filter((a, i) => !a.startsWith("--") && !args[i - 1]?.startsWith("--"));
const fps = Number(flag("--fps", 30)), scale = Number(flag("--scale", 1)), audio = flag("--audio", null);
const stillAt = args.indexOf("--frame") >= 0 ? Number(flag("--frame")) : null;

const { chromium } = loadPlaywright();
const sb = JSON.parse(readFileSync(sbPath, "utf8"));
const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const page = await (await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: scale })).newPage();
await page.goto(pathToFileURL(resolve(here, "player.html")).href);
await page.evaluate(() => document.fonts.ready);
const total = await page.evaluate((s) => window.loadStoryboard(s), sb);

if (stillAt !== null) {
  await page.evaluate((t) => window.renderAt(t), stillAt);
  writeFileSync(args[args.indexOf("--frame") + 2], await page.screenshot());
  await browser.close();
  process.exit(0);
}

const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-i", "-",
  ...(audio ? ["-i", audio] : []), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
  ...(audio ? ["-c:a", "aac", "-b:a", "128k", "-shortest"] : []), "-movflags", "+faststart", outPath], { stdio: ["pipe", "inherit", "inherit"] });
const done = new Promise((res, rej) => { ff.on("close", (c) => (c === 0 ? res() : rej(new Error(`ffmpeg exit ${c}`)))); });
const frames = Math.ceil(total * fps);
for (let i = 0; i < frames; i++) {
  await page.evaluate((t) => window.renderAt(t), i / fps);
  const png = await page.screenshot({ type: "jpeg", quality: 92 });
  if (!ff.stdin.write(png)) await new Promise((r) => ff.stdin.once("drain", r));
}
ff.stdin.end();
await done;
await browser.close();
console.log(`video_render_ok frames=${frames} seconds=${total.toFixed(1)} out=${outPath}`);
