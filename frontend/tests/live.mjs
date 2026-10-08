// Requires a running backend pipeline and the frontend /api proxy.
import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
  });
  await page.goto(process.env.RELAY_UI_URL || "http://127.0.0.1:5173");
  await page.getByRole("button", { name: "Connect your API" }).click();
  await page
    .getByLabel("Workspace token")
    .fill(process.env.RELAY_API_TOKEN || "local-review-token");
  await page.getByRole("button", { name: "Connect workspace" }).click();
  await page.getByText("Live workspace · refreshes every 3 seconds").waitFor();
  await page.getByRole("button", { name: "New incident" }).click();
  const title = `Consumer stopped delivering order events ${Date.now()}`;
  await page.getByLabel("Incident title").fill(title);
  await page.getByLabel("Service", { exact: true }).fill("order-pipeline");
  await page
    .getByLabel("What happened?")
    .fill(
      "The SQS consumer has stopped. Queue backlog is growing and oldest message age exceeds ten minutes. Incoming publish rate is unchanged. No events are acknowledged by the worker.",
    );
  await page.getByRole("button", { name: "Submit for analysis" }).click();
  await page.getByRole("heading", { name: title, level: 2 }).waitFor();
  await page
    .getByRole("button", { name: "Accept direction" })
    .waitFor({ timeout: 45000 });
  assert.match(await page.locator(".classification").innerText(), /queue/i);
  await page
    .getByPlaceholder("What did you find?")
    .fill("Live pipeline check: consumer investigation accepted.");
  await page.getByRole("button", { name: "Accept direction" }).click();
  await page
    .getByText("Saved to the incident record", { exact: false })
    .waitFor();
  await page.reload();
  await page.getByRole("button", { name: "Connect your API" }).click();
  await page
    .getByLabel("Workspace token")
    .fill(process.env.RELAY_API_TOKEN || "local-review-token");
  await page.getByRole("button", { name: "Connect workspace" }).click();
  await page.getByRole("button", { name: new RegExp(title) }).click();
  await page.getByText("Direction accepted", { exact: true }).waitFor();
  assert.equal(await page.evaluate(() => localStorage.length), 0);
  console.log(
    "Live browser pipeline passed: connect, submit, async analysis, persistent review, reload.",
  );
} finally {
  await browser.close();
}
