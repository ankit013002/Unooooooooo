const { test, expect } = require("@playwright/test");

test("two humans can create, join, and start a game", async ({ browser }) => {
  const firstContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const secondContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const first = await firstContext.newPage();
  const second = await secondContext.newPage();
  const errors = [];
  first.on("console", (message) => message.type() === "error" && errors.push(message.text()));
  second.on("console", (message) => message.type() === "error" && errors.push(message.text()));

  await first.goto("http://localhost:8000");
  await first.locator("#create-name").fill("Ankit");
  await first.getByRole("button", { name: /create room/i }).click();
  await expect(first.locator("#lobby-view")).toBeVisible();
  const code = await first.locator("#lobby-code").innerText();
  expect(code).toMatch(/^[A-Z0-9]{4}$/);

  await second.goto(`http://localhost:8000/#${code}`);
  await second.locator("#join-name").fill("Kisu");
  await second.getByRole("button", { name: /join game/i }).click();
  await expect(first.locator("#lobby-players")).toContainText("Kisu");

  await first.locator("#ready-button").click();
  await second.locator("#ready-button").click();
  await expect(first.locator("#game-view")).toBeVisible();
  await expect(second.locator("#game-view")).toBeVisible();
  await expect(first.locator("#player-hand .hand-card")).toHaveCount(7);
  await expect(second.locator("#player-hand .hand-card")).toHaveCount(7);
  await expect(first.locator("#opponents .opponent")).toHaveCount(3);
  await expect(first.locator("#discard-card")).toHaveAttribute("src", /assets\/cards/);

  await first.screenshot({ path: "web-game-desktop.png", fullPage: true });
  await second.screenshot({ path: "web-game-mobile.png", fullPage: true });
  expect(errors).toEqual([]);

  await firstContext.close();
  await secondContext.close();
});
