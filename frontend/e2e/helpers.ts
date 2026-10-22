import { expect, type Page } from "@playwright/test";

let counter = 0;

/** Sign up a brand-new user through the UI and land in the chat. */
export async function signUp(page: Page): Promise<string> {
  const username = `e2e${Date.now()}${++counter}${Math.floor(Math.random() * 1000)}`;
  await page.goto("/signup");
  await page.getByPlaceholder("yourname").fill(username);
  await page.getByPlaceholder("you@example.com").fill(`${username}@example.test`);
  await page.getByPlaceholder("••••••••").fill("e2e-password-1");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/chat$/);
  return username;
}

export async function ask(page: Page, question: string): Promise<void> {
  await page.getByLabel("Message", { exact: true }).fill(question);
  await page.getByLabel("Message", { exact: true }).press("Enter");
}

/** The fake model's canned answer always ends with the question it was asked. */
export const answerTo = (question: string) => `Your question was: "${question}"`;
