import { expect, test } from "@playwright/test";

test("program selection leads to a source-backed alignment explanation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Synthetic demo data.", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Explore program" }).click();
  await expect(page.getByRole("heading", { name: "Synthetic Analytics Program" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "3 documented required-course skills" })).toBeVisible();
  await page.getByRole("link", { name: "Explore jobs with this program" }).click();
  await page.getByRole("link", { name: "Data Analyst Intern" }).click();
  await expect(page.getByRole("heading", { name: "Curriculum alignment" })).toBeVisible();
  await expect(page.getByText("75%", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "SQL · assessed" })).toBeVisible();
  await expect(page.getByText("DEMO101", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Illustrative course evidence" }).first()).toHaveAttribute("href", "https://example.org/vantage/synthetic-curriculum");
});

test("filters and empty states preserve the selected program", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Explore program" }).click();
  await page.getByRole("link", { name: "Explore jobs with this program" }).click();
  await page.getByLabel("Work arrangement").selectOption("remote");
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page.getByRole("heading", { name: "Software Developer Co-op" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Data Analyst Intern" })).toHaveCount(0);
  await expect(page).toHaveURL(/program_id=/);
  await page.getByLabel("Search jobs").fill("unfindablesynthetictoken");
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page.getByRole("heading", { name: "No matching postings" })).toBeVisible();
});
