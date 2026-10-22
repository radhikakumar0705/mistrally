import { expect, test } from "@playwright/test";
import { ask, signUp } from "./helpers";

const NOTES = `# CS101 handbook

## Final project

The final project is codenamed Project KESTREL. Teams of three build a weather dashboard in Go.
`;

test.describe("documents and study mode", () => {
  test("an uploaded document is processed and cited in answers", async ({ page }) => {
    await signUp(page);
    await page.locator('aside input[type="file"]').setInputFiles({
      name: "handbook.md",
      mimeType: "text/markdown",
      buffer: Buffer.from(NOTES),
    });

    // Processed by the background worker; the spinner turns into a document icon
    await expect(page.getByText("handbook.md is ready")).toBeVisible({ timeout: 30_000 });

    await ask(page, "What is Project KESTREL?");
    await expect(page.getByText("handbook.md", { exact: true }).last()).toBeVisible();
    await expect(page.locator("text=Sources")).toBeVisible();
  });

  test("generates a quiz from a topic", async ({ page }) => {
    await signUp(page);
    await page.getByRole("button", { name: "Study" }).click();
    const dialog = page.getByRole("dialog", { name: "Study tools" });
    await dialog.getByLabel("A topic").check();
    await dialog.getByLabel("Topic", { exact: true }).fill("Python lists");
    await dialog.getByRole("button", { name: "Generate quiz" }).click();

    await expect(dialog.getByText(/Answered 0 of \d+/)).toBeVisible();
    await dialog.getByRole("button").filter({ hasText: "Example text 1" }).first().click();
    await expect(dialog.getByText(/Answered 1 of \d+/)).toBeVisible();
  });
});
