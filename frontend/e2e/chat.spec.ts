import { expect, test } from "@playwright/test";
import { answerTo, ask, signUp } from "./helpers";

test.describe("chat", () => {
  test("streams an answer, titles the chat and keeps it after a reload", async ({ page }) => {
    await signUp(page);
    await ask(page, "What is a list comprehension?");

    await expect(page.getByText(answerTo("What is a list comprehension?"))).toBeVisible();
    await expect(page).toHaveURL(/\/chat\/\d+$/);
    await expect(page.getByRole("navigation").getByText("What is a list comprehension?")).toBeVisible();

    await page.reload();
    await expect(page.getByText(answerTo("What is a list comprehension?"))).toBeVisible();
  });

  test("stop halts the answer mid-stream and keeps the partial text", async ({ page }) => {
    await signUp(page);
    await ask(page, "Tell me about recursion");
    await expect(page.getByText("Here's a quick example")).toBeVisible(); // streaming has started
    await page.getByLabel("Stop generating").click();

    await expect(page.getByText("Stopped")).toBeVisible();
    await expect(page.getByLabel("Send message")).toBeVisible();
    await expect(page.getByText(answerTo("Tell me about recursion"))).toHaveCount(0);

    // The partial answer was saved by the server
    await page.reload();
    await expect(page.getByText("Here's a quick example")).toBeVisible();
    await expect(page.getByText(answerTo("Tell me about recursion"))).toHaveCount(0);
  });

  test("stop works while a new chat is still being created", async ({ page }) => {
    await signUp(page);
    await ask(page, "Stop me immediately");
    await page.getByLabel("Stop generating").click();
    await expect(page.getByText("Stopped")).toBeVisible();
    await expect(page.getByText(answerTo("Stop me immediately"))).toHaveCount(0);
  });

  test("exports the conversation as Markdown", async ({ page }) => {
    await signUp(page);
    await ask(page, "Explain recursion");
    await expect(page.getByText(answerTo("Explain recursion"))).toBeVisible();

    const download = page.waitForEvent("download");
    await page.getByLabel("Export chat").click();
    expect((await download).suggestedFilename()).toBe("explain-recursion.md");
  });

  test("runs Python from an answer in the sandbox", async ({ page }) => {
    await signUp(page);
    await ask(page, "Show me a function");
    await page.getByLabel("Run code").click();
    await expect(page.getByText(/Exit code 0/)).toBeVisible();
  });

  test("logging out ends the session", async ({ page }) => {
    await signUp(page);
    await page.getByLabel("Log out").click();
    await expect(page).toHaveURL(/\/login/);
    await page.goto("/chat");
    await expect(page).toHaveURL(/\/login/);
  });
});
