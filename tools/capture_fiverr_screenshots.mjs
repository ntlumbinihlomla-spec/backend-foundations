import { createRequire } from "node:module";
import fs from "node:fs/promises";

const require = createRequire(import.meta.url);
const { chromium } = require(
  "C:/Users/Mathiwe/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright"
);

const chromePath = "C:/Users/Mathiwe/AppData/Local/Google/Chrome/Application/chrome.exe";
const edgePath = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";

async function firstExisting(paths) {
  for (const path of paths) {
    try {
      await fs.access(path);
      return path;
    } catch {
      // Try the next installed browser.
    }
  }
  throw new Error("No installed Chromium browser was found.");
}

const executablePath = await firstExisting([chromePath, edgePath]);
const browser = await chromium.launch({
  headless: true,
  executablePath,
  args: ["--no-sandbox"],
});

const dashboardPath =
  "C:/Users/Mathiwe/backend-foundations/frontend/assets/fiverr-dashboard-screenshot.png";
const reportPath =
  "C:/Users/Mathiwe/backend-foundations/frontend/assets/fiverr-report-screenshot.png";

try {
  const dashboard = await browser.newPage({
    viewport: { width: 1440, height: 1350 },
    deviceScaleFactor: 1,
  });

  await dashboard.goto(
    "http://127.0.0.1:8010/index.html?api=http%3A%2F%2F127.0.0.1%3A8000&key=backend-foundations-demo-key&demo=1&column=amount",
    { waitUntil: "networkidle", timeout: 60000 }
  );
  await dashboard.waitForFunction(
    () =>
      document.body.innerText.includes("Batch summary complete") ||
      document.body.innerText.includes("Grand Total"),
    null,
    { timeout: 60000 }
  );
  await dashboard.screenshot({ path: dashboardPath, fullPage: true });
  const dashboardText = await dashboard.locator("body").innerText();

  const report = await browser.newPage({
    viewport: { width: 1440, height: 1200 },
    deviceScaleFactor: 1,
  });
  await report.setExtraHTTPHeaders({
    "x-api-key": "backend-foundations-demo-key",
  });
  await report.goto(
    "http://127.0.0.1:8000/reports/client?column=amount&files=sales_jan.csv%2Csales_feb.csv%2Csales_mar.csv",
    { waitUntil: "load", timeout: 60000 }
  );
  await report.waitForFunction(
    () =>
      document.body.innerText.includes("Financial CSV Summary Report") &&
      document.body.innerText.includes("Batch Contribution"),
    null,
    { timeout: 60000 }
  );
  await report.screenshot({ path: reportPath, fullPage: true });
  const reportText = await report.locator("body").innerText();

  const dashboardStat = await fs.stat(dashboardPath);
  const reportStat = await fs.stat(reportPath);

  console.log(
    JSON.stringify(
      {
        executablePath,
        dashboardPath,
        reportPath,
        dashboardBytes: dashboardStat.size,
        reportBytes: reportStat.size,
        dashboardHasUploadLibrary: dashboardText.includes("Upload Library"),
        dashboardHasBatch: dashboardText.toLowerCase().includes("grand total"),
        reportHasTitle: reportText.includes("Financial CSV Summary Report"),
        reportHasContribution: reportText.includes("Batch Contribution"),
      },
      null,
      2
    )
  );
} finally {
  await browser.close();
}
