import { createRequire } from "node:module";
import fs from "node:fs/promises";

const require = createRequire(import.meta.url);
const { chromium } = require(
  "C:/Users/Mathiwe/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright"
);

const videoPath = "C:/Users/Mathiwe/backend-foundations/frontend/assets/fiverr-gig-video.mp4";
const browser = await chromium.launch({
  headless: true,
  executablePath: "C:/Users/Mathiwe/AppData/Local/Google/Chrome/Application/chrome.exe",
  args: ["--no-sandbox"],
});

try {
  const bytes = await fs.readFile(videoPath);
  const page = await browser.newPage();
  const metadata = await page.evaluate(async (base64) => {
    const video = document.createElement("video");
    video.src = `data:video/mp4;base64,${base64}`;
    video.muted = true;
    video.playsInline = true;
    document.body.appendChild(video);
    await new Promise((resolve, reject) => {
      video.onloadedmetadata = resolve;
      video.onerror = () => reject(new Error("Video metadata could not be loaded."));
    });
    return {
      duration: video.duration,
      width: video.videoWidth,
      height: video.videoHeight,
      canPlayMp4: video.canPlayType("video/mp4"),
    };
  }, bytes.toString("base64"));

  console.log(
    JSON.stringify(
      {
        path: videoPath,
        bytes: bytes.length,
        megabytes: Number((bytes.length / 1024 / 1024).toFixed(2)),
        ...metadata,
      },
      null,
      2
    )
  );
} finally {
  await browser.close();
}
