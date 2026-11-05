import { createRequire } from "node:module";
import fs from "node:fs/promises";

const require = createRequire(import.meta.url);
const { chromium } = require(
  "C:/Users/Mathiwe/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright"
);

const outPath = "C:/Users/Mathiwe/backend-foundations/frontend/assets/fiverr-gig-video.mp4";
const assets = {
  hero: "C:/Users/Mathiwe/backend-foundations/frontend/assets/financial-dashboard-hero.png",
  dashboard: "C:/Users/Mathiwe/backend-foundations/frontend/assets/fiverr-dashboard-screenshot.png",
  report: "C:/Users/Mathiwe/backend-foundations/frontend/assets/fiverr-report-screenshot.png",
};

async function asDataUrl(path) {
  const bytes = await fs.readFile(path);
  return `data:image/png;base64,${bytes.toString("base64")}`;
}

const imageData = {
  hero: await asDataUrl(assets.hero),
  dashboard: await asDataUrl(assets.dashboard),
  report: await asDataUrl(assets.report),
};

const browser = await chromium.launch({
  headless: true,
  executablePath: "C:/Users/Mathiwe/AppData/Local/Google/Chrome/Application/chrome.exe",
  args: ["--no-sandbox"],
});

try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  const base64 = await page.evaluate(async ({ imageData }) => {
    const width = 1280;
    const height = 720;
    const fps = 30;
    const durationMs = 50000;
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    document.body.style.margin = "0";
    document.body.style.background = "#172633";
    document.body.appendChild(canvas);
    const ctx = canvas.getContext("2d");

    function loadImage(src) {
      return new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => resolve(image);
        image.onerror = reject;
        image.src = src;
      });
    }

    const images = {
      hero: await loadImage(imageData.hero),
      dashboard: await loadImage(imageData.dashboard),
      report: await loadImage(imageData.report),
    };

    function ease(t) {
      return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    }

    function clamp(value, min, max) {
      return Math.max(min, Math.min(max, value));
    }

    function drawCover(image, x, y, w, h, zoom = 1, panX = 0.5, panY = 0.5) {
      const scale = Math.max(w / image.width, h / image.height) * zoom;
      const sw = w / scale;
      const sh = h / scale;
      const sx = clamp((image.width - sw) * panX, 0, image.width - sw);
      const sy = clamp((image.height - sh) * panY, 0, image.height - sh);
      ctx.drawImage(image, sx, sy, sw, sh, x, y, w, h);
    }

    function drawContain(image, x, y, w, h) {
      const scale = Math.min(w / image.width, h / image.height);
      const dw = image.width * scale;
      const dh = image.height * scale;
      ctx.drawImage(image, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh);
    }

    function overlay(alpha = 0.45) {
      ctx.fillStyle = `rgba(9, 20, 30, ${alpha})`;
      ctx.fillRect(0, 0, width, height);
    }

    function panel(x, y, w, h, alpha = 0.92) {
      ctx.fillStyle = `rgba(255, 253, 248, ${alpha})`;
      roundRect(x, y, w, h, 18);
      ctx.fill();
    }

    function roundRect(x, y, w, h, r) {
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.arcTo(x + w, y, x + w, y + h, r);
      ctx.arcTo(x + w, y + h, x, y + h, r);
      ctx.arcTo(x, y + h, x, y, r);
      ctx.arcTo(x, y, x + w, y, r);
      ctx.closePath();
    }

    function text(lines, x, y, options = {}) {
      const {
        size = 44,
        color = "#fffdf8",
        weight = "700",
        lineHeight = 1.08,
        maxWidth = 760,
        align = "left",
        family = "Georgia, serif",
      } = options;
      ctx.fillStyle = color;
      ctx.textAlign = align;
      ctx.textBaseline = "top";
      ctx.font = `${weight} ${size}px ${family}`;
      const lineArray = Array.isArray(lines) ? lines : [lines];
      lineArray.forEach((line, index) => {
        ctx.fillText(line, x, y + index * size * lineHeight, maxWidth);
      });
    }

    function smallCaps(value, x, y, color = "#9ed4bf") {
      ctx.fillStyle = color;
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.font = "700 20px Georgia, serif";
      ctx.fillText(value.toUpperCase(), x, y);
    }

    function button(label, x, y, w = 280) {
      ctx.fillStyle = "#0d6f57";
      roundRect(x, y, w, 58, 8);
      ctx.fill();
      ctx.fillStyle = "#fffdf8";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.font = "700 24px Georgia, serif";
      ctx.fillText(label, x + w / 2, y + 29);
    }

    function drawFrame(ms) {
      const t = ms / 1000;
      ctx.clearRect(0, 0, width, height);

      if (t < 8) {
        const p = ease(t / 8);
        drawCover(images.hero, 0, 0, width, height, 1.02 + p * 0.05, 0.52, 0.52);
        overlay(0.58);
        smallCaps("Financial CSV Dashboard", 70, 72);
        text(["I build dashboards", "for SME financial reports"], 70, 118, {
          size: 60,
          maxWidth: 760,
        });
        text("Upload CSVs, get clean summaries, batch analytics, and client-ready reports.", 72, 282, {
          size: 28,
          weight: "400",
          lineHeight: 1.25,
          maxWidth: 760,
        });
        button("Available on Fiverr", 72, 382, 300);
      } else if (t < 18) {
        const p = ease((t - 8) / 10);
        ctx.fillStyle = "#eef7f4";
        ctx.fillRect(0, 0, width, height);
        drawCover(images.dashboard, 454, 28, 760, 664, 1.05 + p * 0.08, 0.38, 0.22);
        panel(56, 88, 440, 430, 0.96);
        smallCaps("Step 1", 92, 124, "#0d6f57");
        text(["Upload CSV files", "and choose the column"], 92, 170, {
          size: 42,
          color: "#172633",
          maxWidth: 360,
        });
        text("The dashboard turns recurring exports into summary cards your client can read quickly.", 94, 300, {
          size: 24,
          weight: "400",
          color: "#5d6b74",
          lineHeight: 1.28,
          maxWidth: 350,
        });
      } else if (t < 30) {
        const p = ease((t - 18) / 12);
        ctx.fillStyle = "#172633";
        ctx.fillRect(0, 0, width, height);
        drawCover(images.dashboard, 34, 40, 770, 640, 1.22, 0.52, 0.78 - p * 0.08);
        panel(790, 92, 430, 390, 0.97);
        smallCaps("Step 2", 830, 128, "#0d6f57");
        text(["Compare files", "with batch analytics"], 830, 174, {
          size: 40,
          color: "#172633",
          maxWidth: 350,
        });
        text("Totals, averages, and contribution bars make outliers obvious without sending raw spreadsheets.", 832, 300, {
          size: 23,
          weight: "400",
          color: "#5d6b74",
          lineHeight: 1.28,
          maxWidth: 330,
        });
      } else if (t < 41) {
        const p = ease((t - 30) / 11);
        ctx.fillStyle = "#f4f2ec";
        ctx.fillRect(0, 0, width, height);
        drawContain(images.report, 72, 36, 730, 648);
        panel(790, 114, 420, 370, 0.97);
        smallCaps("Step 3", 830, 150, "#0d6f57");
        text(["Export a clean", "client report"], 830, 196, {
          size: 42,
          color: "#172633",
          maxWidth: 340,
        });
        text("Open the report, review totals, show contribution bars, then print or save as PDF.", 832, 324, {
          size: 23,
          weight: "400",
          color: "#5d6b74",
          lineHeight: 1.28,
          maxWidth: 340,
        });
        ctx.globalAlpha = 0.12 + p * 0.08;
        drawCover(images.hero, 0, 0, width, height, 1.2, 0.5, 0.5);
        ctx.globalAlpha = 1;
      } else {
        const p = ease((t - 41) / 9);
        drawCover(images.hero, 0, 0, width, height, 1.08 + p * 0.04, 0.5, 0.5);
        overlay(0.68);
        smallCaps("Fixed-price dashboard pilot", 70, 92);
        text(["CSV Report Pilot", "Dashboard Build", "Monthly Support"], 70, 138, {
          size: 52,
          maxWidth: 760,
        });
        text("Send a sanitized sample CSV and I will confirm the best package or custom offer.", 72, 338, {
          size: 28,
          weight: "400",
          lineHeight: 1.24,
          maxWidth: 720,
        });
        button("Order on Fiverr", 72, 448, 260);
      }
    }

    const stream = canvas.captureStream(fps);
    const recorder = new MediaRecorder(stream, {
      mimeType: "video/mp4;codecs=avc1.42E01E",
      videoBitsPerSecond: 2400000,
    });
    const chunks = [];
    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size) chunks.push(event.data);
    };

    recorder.start(1000);
    const start = performance.now();
    await new Promise((resolve) => {
      function tick(now) {
        const elapsed = now - start;
        drawFrame(elapsed);
        if (elapsed < durationMs) {
          requestAnimationFrame(tick);
        } else {
          drawFrame(durationMs);
          resolve();
        }
      }
      requestAnimationFrame(tick);
    });
    await new Promise((resolve) => {
      recorder.onstop = resolve;
      recorder.stop();
    });

    const blob = new Blob(chunks, { type: "video/mp4" });
    const buffer = await blob.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let index = 0; index < bytes.length; index += 1) {
      binary += String.fromCharCode(bytes[index]);
    }
    return btoa(binary);
  }, { imageData });

  await fs.writeFile(outPath, Buffer.from(base64, "base64"));
  const stat = await fs.stat(outPath);
  console.log(JSON.stringify({ outPath, bytes: stat.size }, null, 2));
} finally {
  await browser.close();
}
