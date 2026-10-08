// Run against a local Vite server: npm run dev, then npm run smoke.
import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(process.env.RELAY_UI_URL || "http://127.0.0.1:5173");
  await page.getByRole("heading", { name: "Find the signal." }).waitFor();
  await page.getByRole("button", { name: /Order events waiting/ }).click();
  await page
    .getByRole("heading", {
      name: "Order events waiting for a consumer",
      level: 2,
    })
    .waitFor();
  assert.match(await page.locator(".classification").innerText(), /queue/i);
  await page.locator(".evidence > button").first().click();
  assert.equal(await page.locator(".evidence-body").count(), 1);
  await page
    .getByPlaceholder("What did you find?")
    .fill("Consumer restored; backlog draining.");
  await page.getByRole("button", { name: "Accept direction" }).click();
  await page.getByText("Direction accepted", { exact: true }).waitFor();
  await page.getByRole("button", { name: /^Reviewed/ }).click();
  assert.equal(await page.locator(".incident-row").count(), 1);
  await page.getByRole("button", { name: /^Incident inbox/ }).click();
  await page.getByLabel("Filter priority").selectOption("P1");
  assert.equal(await page.locator(".incident-row").count(), 1);
  await page.getByLabel("Filter priority").selectOption("all");
  await page.getByRole("button", { name: /Unusual support report/ }).click();
  await page.getByText("More context needed", { exact: true }).waitFor();
  await page.getByRole("button", { name: /Checkout latency/ }).click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "/tmp/relay-desktop.png", fullPage: true });
  await page.getByRole("button", { name: "New incident" }).click();
  await page.getByRole("dialog").waitFor();
  await page.getByLabel("Workspace token").fill("invalid");
  await page.getByRole("button", { name: "Connect workspace" }).click();
  await page.locator('[role="dialog"] [role="alert"]').waitFor();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "/tmp/relay-mobile.png", fullPage: true });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  assert.deepEqual(errors, []);
  console.log(
    "Browser smoke passed: selection, evidence, review, filtering, abstention, connection failure, mobile layout.",
  );
} finally {
  await browser.close();
}
