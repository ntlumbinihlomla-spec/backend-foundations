import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require(
  "C:/Users/Mathiwe/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright"
);

const browser = await chromium.launch({
  headless: true,
  executablePath: "C:/Users/Mathiwe/AppData/Local/Google/Chrome/Application/chrome.exe",
  args: ["--no-sandbox"],
});

try {
  const page = await browser.newPage();
  const support = await page.evaluate(() => {
    const types = [
      "video/mp4",
      "video/mp4;codecs=avc1.42E01E",
      "video/mp4;codecs=h264",
      "video/webm;codecs=vp9",
      "video/webm;codecs=vp8",
      "video/webm",
    ];
    return Object.fromEntries(types.map((type) => [type, MediaRecorder.isTypeSupported(type)]));
  });
  console.log(JSON.stringify(support, null, 2));
} finally {
  await browser.close();
}
