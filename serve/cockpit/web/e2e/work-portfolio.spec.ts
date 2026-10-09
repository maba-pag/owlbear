import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, type Locator, type Page, test } from "@playwright/test";

function requirePresent<T>(value: T | null | undefined): T {
  if (value === null || value === undefined) {
    throw new Error("Expected value to be present");
  }
  return value;
}

async function visibleRows(page: Page): Promise<Locator> {
  return page.locator("[data-work-item]").filter({ visible: true });
}

async function inspect(page: Page, title: string, detailTitle = title): Promise<{ detail: Locator; trigger: Locator }> {
  const row = (await visibleRows(page)).filter({ hasText: title });
  const trigger = row.getByRole("link", { name: new RegExp(`^${title}`) });
  await trigger.click();
  const detail = page.getByTestId("work-item-detail");
  await expect(detail.getByRole("heading", { name: detailTitle, exact: true })).toBeVisible();
  await expect(page.getByRole("dialog", { name: "Work Item detail" })).toBeVisible();
  await expect(page.getByTestId("work-portfolio-table")).toBeVisible();
  await expect(page).toHaveURL(/\/delivery\/[^/]+\/[^/]+$/);
  return { detail, trigger };
}

async function returnToPortfolio(page: Page, trigger: Locator): Promise<void> {
  await page.getByRole("button", { name: "Dismiss flyout" }).click();
  await expect(page.getByTestId("work-item-detail")).not.toBeVisible();
  await expect(page.getByRole("dialog", { name: "Work Item detail" })).not.toBeVisible();
  await expect(page).toHaveURL(/\/delivery$/);
  await expect(trigger).toBeFocused();
}

async function selectValue(locator: Locator, value: string): Promise<void> {
  await locator.evaluate((element, selected) => {
    (element as HTMLElement & { value: string }).value = selected;
    element.dispatchEvent(new CustomEvent("change", { detail: { value: selected }, bubbles: true }));
  }, value);
}

async function inputValue(locator: Locator, value: string): Promise<void> {
  await locator.evaluate((element, input) => {
    (element as HTMLElement & { value: string }).value = input;
    element.dispatchEvent(new CustomEvent("input", { detail: { value: input }, bubbles: true }));
  }, value);
}

async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  const overflow = await page.evaluate(() => ({
    document: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    tables: [...document.querySelectorAll<HTMLElement>('[data-testid="work-table-scroll"]')]
      .filter((table) => table.getBoundingClientRect().height > 0)
      .map((table) => table.scrollWidth - table.clientWidth),
  }));
  expect(overflow.document).toBeLessThanOrEqual(0);
  expect(overflow.tables.every((value) => value <= 1)).toBe(true);
}

async function flyoutPanelBox(page: Page): Promise<{ x: number; y: number; width: number; height: number } | null> {
  return page
    .locator("p-flyout")
    .last()
    .evaluate((element) => {
      const panel = element.shadowRoot?.querySelector(".flyout");
      if (!panel) return null;
      const box = panel.getBoundingClientRect();
      return { x: box.x, y: box.y, width: box.width, height: box.height };
    });
}

function formatViolations(violations: Array<{ id: string; impact?: string | null; help: string }>): string {
  return violations.map((item) => `[${item.impact ?? "unknown"} ${item.id}] ${item.help}`).join("\n");
}

async function normalizeSeedLifecycleStatuses(page: Page): Promise<void> {
  await page.route("**/api/work-items", async (route) => {
    const response = await route.fetch();
    const payload = (await response.json()) as {
      operating: { statuses: Array<Record<string, unknown>> };
    };
    const statuses = payload.operating.statuses.map((status) => {
      if (status.change_id === "work-e2e") {
        return {
          ...status,
          admission: "admitted",
          stage: "design",
          actionable_runtime: true,
          diagnostic_code: null,
          diagnostic_detail: null,
        };
      }
      return status;
    });
    await route.fulfill({
      response,
      body: JSON.stringify({
        ...payload,
        operating: { ...payload.operating, statuses },
      }),
    });
  });
}

test.describe("assembled Delivery portfolio", () => {
  test.describe.configure({ mode: "serial" });

  test.beforeEach(async ({ page }) => {
    await normalizeSeedLifecycleStatuses(page);
  });

  test.afterEach(async ({ page }) => {
    await page.unrouteAll({ behavior: "ignoreErrors" });
  });

  test("wide workspace explains operating state and provides routed detail", async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto("/work");
    await expect(page).toHaveURL(/\/delivery$/);

    const table = page.getByTestId("work-portfolio-table");
    await expect(table).toBeVisible();
    await expect(await visibleRows(page)).toHaveCount(9);
    await expect(table).toContainText("Work portfolio E2E");
    for (const column of ["Work", "State"]) {
      await expect(table.getByRole("columnheader", { name: column })).toHaveCount(2);
    }
    const tableHeaders = table.locator("thead");
    await expect(tableHeaders).toHaveCount(2);
    await expect(tableHeaders.nth(0)).toHaveClass(/sr-only/);
    await expect(tableHeaders.nth(1)).toHaveClass(/sr-only/);
    await expect(table).toContainText("Your decision");
    await expect(table).toContainText("Ready for finalization");
    await expect(table).toContainText("Waiting for OUT-002 to complete.");
    await expect(table).toContainText("This Outcome is complete.");
    await expect(table).not.toContainText("Reviewed");

    const summary = page.getByLabel("Delivery portfolio status");
    await expect(summary).toContainText("3Changes");
    await expect(summary).toContainText("2Design");
    await expect(summary).toContainText("1Delivery");
    await expect(summary).toContainText("2Ready");
    await expect(summary).toContainText("2Needs you");

    const needsYou = summary.getByRole("button", {
      name: "Filter to 2 work items: Needs you",
    });
    await needsYou.click();
    await expect(needsYou).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByTestId("work-filter-chip-needs")).toBeVisible();
    await needsYou.click();
    await expect(needsYou).toHaveAttribute("aria-pressed", "false");
    await expect(page.getByTestId("work-filter-chip-needs")).not.toBeVisible();
    await expect(await visibleRows(page)).toHaveCount(9);

    const guidance = page.getByLabel("Delivery guidance");
    await expect(guidance).toContainText("Review 2 items that need you");
    await expect(guidance).toContainText("No session action needed.");
    await expect(guidance).toContainText("Continue Design for:");
    await expect(
      guidance.getByTestId("portfolio-commands").getByText("/design design-operations-roadmap", { exact: true }),
    ).toBeVisible();
    const tableBox = await table.boundingBox();
    const guidanceBox = await guidance.boundingBox();
    expect(tableBox).not.toBeNull();
    expect(guidanceBox).not.toBeNull();
    const tableBounds = requirePresent(tableBox);
    const guidanceBounds = requirePresent(guidanceBox);
    expect(guidanceBounds.y).toBeGreaterThanOrEqual(tableBounds.y + tableBounds.height);

    const publicationRow = page.getByLabel("Change publication for Publication release");
    await expect(publicationRow).toContainText("Publication");
    await expect(publicationRow).toContainText("Change: Publication release");
    await expect(publicationRow).toContainText("Ready for finalization");
    await expect(publicationRow.locator("dt")).toHaveText(["Work", "State"]);
    await expect(publicationRow.locator("dd")).toHaveCount(2);

    const normalOutcome = (await visibleRows(page)).filter({ hasText: "Publish operator guide" }).locator("td").first();
    await expect(normalOutcome).toHaveCSS("border-left-width", "4px");
    await expect(normalOutcome).toHaveCSS("border-top-width", "1px");
    await expect(normalOutcome).toHaveCSS("border-top-left-radius", "8px");
    const interventionOutcome = (await visibleRows(page))
      .filter({ hasText: "Choose release mode" })
      .locator("td")
      .first();
    await expect(interventionOutcome).toHaveCSS("border-left-width", "4px");
    await expect(publicationRow).toHaveCSS("border-left-width", "4px");

    const publicationTrigger = publicationRow.getByRole("link", {
      name: "Publication",
      exact: true,
    });
    const publicationStatusBox = await publicationRow
      .getByText("Ready for finalization", { exact: true })
      .last()
      .boundingBox();
    expect(publicationStatusBox).not.toBeNull();
    const publicationStatusBounds = requirePresent(publicationStatusBox);
    const publicationHitTarget = await page.evaluate(
      ({ x, y }) => {
        const element = document.elementFromPoint(x, y);
        const link = element?.closest("a");
        return {
          cursor: element ? getComputedStyle(element).cursor : null,
          href: link?.getAttribute("href") ?? null,
        };
      },
      {
        x: publicationStatusBounds.x + publicationStatusBounds.width / 2,
        y: publicationStatusBounds.y + publicationStatusBounds.height / 2,
      },
    );
    expect(publicationHitTarget.cursor).toBe("pointer");
    expect(publicationHitTarget.href).toBe("/delivery/publication-e2e/publication");
    await page.mouse.click(
      publicationStatusBounds.x + publicationStatusBounds.width / 2,
      publicationStatusBounds.y + publicationStatusBounds.height / 2,
    );
    await expect(
      page.getByTestId("work-item-detail").getByRole("heading", { name: "Publication", exact: true }),
    ).toBeVisible();
    const publicationFlyoutBox = await flyoutPanelBox(page);
    expect(publicationFlyoutBox).not.toBeNull();
    const publicationFlyoutBounds = requirePresent(publicationFlyoutBox);
    await page.mouse.click(
      publicationFlyoutBounds.x / 2,
      publicationFlyoutBounds.y + publicationFlyoutBounds.height / 2,
    );
    await expect(page.getByTestId("work-item-detail")).not.toBeVisible();
    await expect(publicationTrigger).toBeFocused();
    await expect.poll(() => publicationTrigger.evaluate((element) => element.matches(":focus-visible"))).toBe(false);

    await publicationTrigger.focus();
    await page.keyboard.press("Enter");
    await expect(
      page.getByTestId("work-item-detail").getByRole("heading", { name: "Publication", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Dismiss flyout" }).focus();
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("work-item-detail")).not.toBeVisible();
    await expect(publicationTrigger).toBeFocused();
    await expect.poll(() => publicationTrigger.evaluate((element) => element.matches(":focus-visible"))).toBe(true);

    const designSection = page.getByTestId("design-work-section");
    await expect(designSection).toContainText("Design Operations Roadmap");
    await expect(designSection).toContainText("Not admitted to Delivery");
    await expect(designSection.getByRole("heading", { name: "Design work" })).toHaveCSS("border-bottom-width", "1px");
    const designRow = designSection.locator("[data-work-item]");
    await expect(designRow).toHaveCSS("border-left-width", "4px");
    await expect(designRow).toHaveCSS("border-top-left-radius", "8px");
    await expect(designRow.locator("dt")).toHaveText(["Work", "State"]);
    await expect(designRow.locator("dd")).toHaveCount(2);
    const firstChange = table.locator(":scope > section").first();
    const [changeHeadingBox, changeRowBox, designBox, designHeadingBox, designRowBox] = await Promise.all([
      firstChange.getByRole("heading").first().boundingBox(),
      firstChange.locator("tbody tr").first().boundingBox(),
      designSection.boundingBox(),
      designSection.getByRole("heading", { name: "Design work" }).boundingBox(),
      designRow.boundingBox(),
    ]);
    expect(changeHeadingBox).not.toBeNull();
    expect(changeRowBox).not.toBeNull();
    expect(designBox).not.toBeNull();
    expect(designHeadingBox).not.toBeNull();
    expect(designRowBox).not.toBeNull();
    const changeHeadingBounds = requirePresent(changeHeadingBox);
    const changeRowBounds = requirePresent(changeRowBox);
    const designBounds = requirePresent(designBox);
    const designHeadingBounds = requirePresent(designHeadingBox);
    const designRowBounds = requirePresent(designRowBox);
    expect(changeRowBounds.y).toBeGreaterThanOrEqual(changeHeadingBounds.y + changeHeadingBounds.height);
    expect(designRowBounds.y - (designHeadingBounds.y + designHeadingBounds.height)).toBeCloseTo(8, 0);
    expect(designBounds.y - (tableBounds.y + tableBounds.height)).toBeCloseTo(32, 0);
    expect(guidanceBounds.y - (designBounds.y + designBounds.height)).toBeCloseTo(32, 0);
    await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
    const designCommand = "/design design-operations-roadmap";
    const designCommandButton = designRow.getByRole("button", {
      name: `Copy command ${designCommand}`,
    });
    await expect(designCommandButton).toHaveCount(0);
    await guidance.scrollIntoViewIfNeeded();
    const guidanceCommand = guidance
      .getByTestId("portfolio-commands")
      .getByRole("button", { name: `Copy command ${designCommand}` });
    for (const commandButton of [guidanceCommand]) {
      const visualContract = await commandButton.evaluate((button) => {
        const code = button.querySelector("code");
        const icon = button.querySelector("p-icon");
        if (!code || !icon) return null;
        const buttonStyle = getComputedStyle(button);
        const codeBox = code.getBoundingClientRect();
        const iconBox = icon.getBoundingClientRect();
        return {
          fontSize: buttonStyle.fontSize,
          color: buttonStyle.color,
          iconName: (icon as HTMLElement & { name?: string }).name,
          centerDelta: Math.abs(iconBox.top + iconBox.height / 2 - (codeBox.top + codeBox.height / 2)),
          codeInsideButton: button.contains(code),
        };
      });
      expect(visualContract).not.toBeNull();
      const visual = requirePresent(visualContract);
      expect(visual.fontSize).toBe("13px");
      expect(visual.color).toBe("rgba(17, 17, 19, 0.6)");
      expect(visual.iconName).toBe("ai-code");
      expect(visual.centerDelta).toBeLessThanOrEqual(1);
      expect(visual.codeInsideButton).toBe(true);
    }
    const guidanceItems = guidance.getByTestId("portfolio-next-session").locator("li");
    const guidanceLayout = await guidanceItems.evaluateAll((items) => {
      const list = items[0]?.parentElement;
      const boxes = items.map((item) => item.getBoundingClientRect());
      return {
        display: list ? getComputedStyle(list).display : null,
        adjacentGap: boxes.length > 1 ? boxes[1].left - boxes[0].right : null,
      };
    });
    expect(guidanceLayout.display).toBe("flex");
    expect(guidanceLayout.adjacentGap).not.toBeNull();
    const adjacentGap = requirePresent(guidanceLayout.adjacentGap);
    expect(adjacentGap).toBeGreaterThanOrEqual(32);
    expect(adjacentGap).toBeLessThanOrEqual(64);
    await expect(designCommandButton).toHaveCount(0);
    await page.screenshot({
      path: testInfo.outputPath("delivery-command-alignment.png"),
    });
    await guidanceCommand.locator("code").click();
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(designCommand);
    await expect(page).toHaveURL(/\/delivery$/);
    const designTrigger = designSection.getByRole("link", {
      name: "Design Operations Roadmap",
    });
    await designTrigger.click();
    const designDetail = page.getByTestId("design-work-detail");
    await expect(designDetail).toContainText("Coordinate the next focused Delivery change.");
    const detailCommand = designDetail.getByRole("button", {
      name: `Copy command ${designCommand}`,
    });
    await expect(detailCommand).toBeVisible();
    const detailCommandLayout = await detailCommand.evaluate((button) => {
      const label = button.previousElementSibling;
      if (!label) return null;
      const labelBox = label.getBoundingClientRect();
      const buttonBox = button.getBoundingClientRect();
      return {
        centerDelta: Math.abs(labelBox.top + labelBox.height / 2 - (buttonBox.top + buttonBox.height / 2)),
        gap: buttonBox.left - labelBox.right,
      };
    });
    expect(detailCommandLayout).not.toBeNull();
    const detailLayout = requirePresent(detailCommandLayout);
    expect(detailLayout.centerDelta).toBeLessThanOrEqual(1);
    expect(detailLayout.gap).toBeGreaterThanOrEqual(8);
    await page.reload();
    await expect(designDetail.locator("h1").first()).toHaveText("Design Operations Roadmap");
    await page.getByRole("button", { name: "Dismiss flyout" }).click();
    await expect(designDetail).not.toBeVisible();
    await expect(page).toHaveURL(/\/delivery$/);

    const filterToggle = page.getByTestId("work-filters-toggle");
    await expect(filterToggle).toHaveAttribute("aria-controls", "work-filters-panel");
    await filterToggle.click();
    await expect(filterToggle).toHaveAttribute("aria-expanded", "true");
    await expect(page.getByTestId("work-filters-panel")).toBeVisible();
    await selectValue(page.locator('p-select[name="work-needs-filter"]'), "you");
    await expect(page.getByTestId("work-shown-count")).toContainText("3 of 9");
    await expect(page.getByTestId("design-work-section")).toBeVisible();
    await selectValue(page.locator('p-select[name="work-needs-filter"]'), "dependency");
    await expect(page.getByTestId("work-shown-count")).toContainText("1 of 9");
    await expect(page.getByTestId("design-work-section")).not.toBeVisible();
    await expect(await visibleRows(page)).toHaveCount(1);
    await page.getByTestId("work-filters-reset").click();
    await expect(await visibleRows(page)).toHaveCount(9);
    await page.getByTestId("work-filters-toggle").click();

    const returnedRow = (await visibleRows(page)).filter({
      hasText: "Plan release notes",
    });
    const returnedTrigger = returnedRow.getByRole("link", {
      name: /^Plan release notes/,
    });
    const progressCell = returnedRow.locator("td").nth(1);
    const progressBox = await progressCell.boundingBox();
    expect(progressBox).not.toBeNull();
    const progressBounds = requirePresent(progressBox);
    await page.mouse.click(progressBounds.x + progressBounds.width / 2, progressBounds.y + progressBounds.height / 2);
    const returnedDetail = page.getByTestId("work-item-detail");
    await expect(returnedDetail.getByRole("heading", { name: "Plan release notes" })).toBeVisible();
    await expect(returnedDetail).toContainText("Returned to Design");
    await expect(returnedDetail).toContainText("Evidence: request:release-notes-authority");
    await expect(returnedDetail).toContainText("Source boundary: design:release-notes-v2");
    await returnToPortfolio(page, returnedTrigger);

    const requestRow = (await visibleRows(page)).filter({
      hasText: "Choose release mode",
    });
    const requestTrigger = requestRow.getByRole("link", {
      name: /^Choose release mode/,
    });
    const requestAction = requestRow.locator("p-link-pure", {
      hasText: "Answer request",
    });
    await expect(requestAction).toHaveJSProperty("href", "/delivery/work-e2e/outcome%3AOUT-001#open-request");
    await requestAction.click();
    let inspected = {
      detail: page.getByTestId("work-item-detail"),
      trigger: requestTrigger,
    };
    await expect(inspected.detail.getByRole("heading", { name: "Choose release mode" })).toBeVisible();
    await expect(inspected.detail.getByTestId("request-request-release-mode")).toBeFocused();
    await expect(page.getByTestId("work-portfolio-table")).toBeVisible();
    await expect(inspected.detail).toContainText("Resolve the bounded release decision.");
    await expect(inspected.detail).toContainText("Observe Choose release mode.");
    await expectNoHorizontalOverflow(page);
    await selectValue(inspected.detail.locator('p-select[name="request-request-release-mode-option"]'), "safe");
    const answerResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" && response.url().includes("/requests/request-release-mode/answer"),
    );
    await inspected.detail.getByText("Submit answer", { exact: true }).click();
    expect((await answerResponse).status()).toBe(200);
    await expect(inspected.detail).toContainText("Safe rollout");
    await returnToPortfolio(page, inspected.trigger);

    inspected = await inspect(page, "Publication");
    await expect(inspected.detail).toContainText("Ready for finalization");
    await expect(inspected.detail).toContainText("Next: merge the latest target into this Change");
    await expect(inspected.detail).not.toContainText("Finalize the reviewed Change");
    await expect(inspected.detail.getByTestId("publication-readiness-status")).toHaveText("Ready for next step");
    await expect(
      inspected.detail.locator('section[aria-labelledby="work-publication-heading"] [data-section-tone="neutral"]'),
    ).toBeVisible();
    await expect(inspected.detail.locator('[data-section-tone="warning"]')).toHaveCount(0);
    await expect(inspected.detail).not.toContainText(/merge now/i);
    await page.screenshot({
      path: testInfo.outputPath("delivery-wide-publication-detail.png"),
      fullPage: true,
    });
    await returnToPortfolio(page, inspected.trigger);

    inspected = await inspect(page, "Build operator controls");
    await expect(inspected.detail).toContainText("Build OUT-002");
    await returnToPortfolio(page, inspected.trigger);

    inspected = await inspect(page, "Finalize release");
    const parentScrollHeight = await page
      .getByTestId("work-scroll-surface")
      .evaluate((element) => element.scrollHeight);
    await inspected.detail.getByText("Administrative actions", { exact: true }).click();
    await expect
      .poll(() => page.getByTestId("work-scroll-surface").evaluate((element) => element.scrollHeight))
      .toBe(parentScrollHeight);
    const nestedScrollers = await inspected.detail.locator("*").evaluateAll(
      (elements) =>
        elements.filter((element) => {
          const style = getComputedStyle(element);
          return ["auto", "scroll"].includes(style.overflowY) && element.scrollHeight > element.clientHeight;
        }).length,
    );
    expect(nestedScrollers).toBe(0);
    await selectValue(inspected.detail.locator('p-select[name="backward-stage"]'), "planning");
    await inputValue(inspected.detail.locator('p-input-text[name="backward-reason"]'), "Authority changed");
    const previewResponse = page.waitForResponse(
      (response) => response.request().method() === "POST" && response.url().endsWith("/move-backward/preview"),
    );
    await inspected.detail.getByText("Review backward move", { exact: true }).click();
    expect((await previewResponse).status()).toBe(200);
    const modal = page.locator("p-modal").filter({ hasText: "The following Outcomes will be reset:" });
    await expect(modal).toContainText("OUT-003");
    const moveResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" && response.url().endsWith("/outcomes/OUT-003/move-backward"),
    );
    await modal.getByText("Confirm backward move", { exact: true }).click();
    expect((await moveResponse).status()).toBe(200);
    await expect(inspected.detail).toContainText("Moved backward. Reset: OUT-003.");
    await returnToPortfolio(page, inspected.trigger);

    await expectNoHorizontalOverflow(page);
    const accessibility = await new AxeBuilder({ page }).analyze();
    const blocking = accessibility.violations.filter(
      (violation) => violation.impact === "serious" || violation.impact === "critical",
    );
    expect(blocking, formatViolations(blocking)).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath("delivery-wide-table.png"),
      fullPage: true,
    });
  });

  test("compact workspace uses a fullscreen flyout and restores row focus", async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/delivery");

    await expect(await visibleRows(page)).toHaveCount(9);
    await expect(page.getByTestId("design-work-section")).toBeVisible();
    const guidance = page.getByLabel("Delivery guidance");
    await expect(guidance.getByTestId("portfolio-next-session").locator("li")).toHaveCount(3);
    await expect(page.getByTestId("work-portfolio-table")).toBeVisible();
    await expectNoHorizontalOverflow(page);

    const designCommand = "/design design-operations-roadmap";
    const compactCommand = guidance.getByRole("button", {
      name: `Copy command ${designCommand}`,
    });
    const compactCommandLayout = await compactCommand.evaluate((button) => {
      const code = button.querySelector("code");
      const icon = button.querySelector("p-icon") as (HTMLElement & { name?: string }) | null;
      if (!code || !icon) return null;
      const buttonBox = button.getBoundingClientRect();
      const codeBox = code.getBoundingClientRect();
      const iconBox = icon.getBoundingClientRect();
      return {
        iconName: icon.name,
        firstLineDelta: Math.abs(iconBox.top - codeBox.top),
        overflow: button.scrollWidth - button.clientWidth,
        contained: codeBox.right <= buttonBox.right,
      };
    });
    expect(compactCommandLayout).not.toBeNull();
    const compactLayout = requirePresent(compactCommandLayout);
    expect(compactLayout.iconName).toBe("ai-code");
    expect(compactLayout.firstLineDelta).toBeLessThanOrEqual(1);
    expect(compactLayout.overflow).toBe(0);
    expect(compactLayout.contained).toBe(true);

    const inspected = await inspect(page, "Build operator controls");
    await expect(page.getByRole("button", { name: "Dismiss flyout" })).toBeVisible();
    await expect(inspected.detail).toContainText("Build OUT-002");
    const flyoutBox = await flyoutPanelBox(page);
    expect(flyoutBox).not.toBeNull();
    expect(requirePresent(flyoutBox).width).toBeGreaterThan(380);
    await page.screenshot({
      path: testInfo.outputPath("delivery-compact-flyout.png"),
    });
    await returnToPortfolio(page, inspected.trigger);

    await expectNoHorizontalOverflow(page);
  });

  test("mobile rows preserve field semantics without overflow", async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/delivery");

    const rows = await visibleRows(page);
    await expect(rows).toHaveCount(9);
    const publicationRow = page.getByLabel("Change publication for Publication release");
    await expect(publicationRow.locator("dt")).toHaveText(["Work", "State"]);
    await expect(publicationRow.locator("dt").first()).toHaveClass(/sr-only/);
    await expect(publicationRow.locator("dd")).toHaveCount(2);
    await expect(publicationRow).toHaveAttribute("aria-label", "Change publication for Publication release");
    await expectNoHorizontalOverflow(page);
    const accessibility = await new AxeBuilder({ page }).analyze();
    const blocking = accessibility.violations.filter(
      (violation) => violation.impact === "serious" || violation.impact === "critical",
    );
    expect(blocking, formatViolations(blocking)).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath("delivery-mobile-rows.png"),
      fullPage: true,
    });
  });

  test("filter popover preserves portfolio position and supports real selection", async ({ page }) => {
    for (const width of [1177, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/delivery");

      const table = page.getByTestId("work-portfolio-table");
      await expect(table).toBeVisible();
      const closedBox = await table.boundingBox();
      expect(closedBox).not.toBeNull();

      const toggle = page.getByTestId("work-filters-toggle");
      await toggle.click();
      await expect(page.getByTestId("work-filters-panel")).toBeVisible();
      const openBox = await table.boundingBox();
      expect(openBox).not.toBeNull();
      expect(requirePresent(openBox).y).toBe(requirePresent(closedBox).y);

      const attention = page.getByRole("combobox", { name: "Attention" });
      await attention.click();
      await page.getByRole("option", { name: "Needs you", exact: true }).click();
      await expect(page.getByTestId("work-shown-count")).toContainText("of 9");
      await expect(page.getByTestId("work-filter-chip-needs")).toBeVisible();
      await expect(page.getByTestId("work-filters-panel")).toBeVisible();

      await page.keyboard.press("Escape");
      await expect(page.getByTestId("work-filters-panel")).not.toBeVisible();
      await expect(toggle).toBeFocused();

      await toggle.click();
      await expect(page.getByTestId("work-filters-panel")).toBeVisible();
      await page.getByRole("heading", { name: "Work portfolio E2E", exact: true }).click();
      await expect(page.getByTestId("work-filters-panel")).not.toBeVisible();
      await expect(toggle).toBeFocused();
    }
  });

  test("filter popover fits the compact viewport without horizontal overflow", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/delivery");

    const toggle = page.getByTestId("work-filters-toggle");
    await toggle.click();
    const panel = page.getByTestId("work-filters-panel");
    await expect(panel).toBeVisible();
    const panelBox = await panel.boundingBox();
    expect(panelBox).not.toBeNull();
    const panelBounds = requirePresent(panelBox);
    expect(panelBounds.x).toBeGreaterThanOrEqual(0);
    expect(panelBounds.x + panelBounds.width).toBeLessThanOrEqual(390);
    await expect(panel.getByRole("combobox", { name: "Change" })).toBeVisible();
    await expect(panel.getByRole("combobox", { name: "Attention" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });

  test("desktop workspaces keep columns and overview context beside detail", async ({ page }) => {
    for (const width of [1024, 1280]) {
      await page.setViewportSize({ width, height: 800 });
      await page.goto("/delivery");

      const table = page.getByTestId("work-table-scroll").first();
      await expect(table).toBeVisible();
      await expect(table.getByRole("columnheader", { name: "Work" })).toBeVisible();
      const inspected = await inspect(page, "Build operator controls");
      await expect(inspected.detail).toContainText("Build OUT-002");
      const flyoutBox = await flyoutPanelBox(page);
      expect(flyoutBox).not.toBeNull();
      expect(requirePresent(flyoutBox).width).toBeLessThan(width);
      await expect(page.getByTestId("work-portfolio-table")).toBeVisible();
      await expectNoHorizontalOverflow(page);
      await returnToPortfolio(page, inspected.trigger);
    }
  });

  test("wide detail flyout preserves overview context without horizontal scrolling", async ({ page }) => {
    await page.setViewportSize({ width: 1408, height: 800 });
    await page.goto("/delivery");

    const inspected = await inspect(page, "Build operator controls");
    await expect(inspected.detail).toContainText("Build OUT-002");
    const [surfaceBox, flyoutBox] = await Promise.all([
      page.getByTestId("work-scroll-surface").boundingBox(),
      flyoutPanelBox(page),
    ]);
    expect(surfaceBox).not.toBeNull();
    expect(flyoutBox).not.toBeNull();
    const surfaceBounds = requirePresent(surfaceBox);
    const flyoutBounds = requirePresent(flyoutBox);
    expect(flyoutBounds.width).toBeGreaterThan(surfaceBounds.width * 0.55);
    expect(flyoutBounds.width).toBeLessThan(surfaceBounds.width * 0.75);
    await expectNoHorizontalOverflow(page);
  });

  test("routed detail survives reload and completed history remains reachable", async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1440, height: 760 });
    await page.goto("/delivery/work-e2e/outcome%3AOUT-005");

    const detail = page.getByTestId("work-item-detail");
    await expect(detail.getByRole("heading", { name: "Publish operator guide" })).toBeVisible();
    await expect(detail).toContainText("Delivery task evidence");
    const evidence = detail.getByTestId("evidence-summary");
    await evidence.locator("summary").click();
    await expect(evidence).toContainText("Acceptance evidence (1 covered)");
    await expect(evidence.getByTestId("evidence-OUT-005.01")).toContainText("Covered");
    await expect(evidence.getByTestId("evidence-locator")).toHaveText("path:reports/assembled-cockpit.txt");
    await expect(evidence.getByRole("link")).toHaveCount(0);
    await page.reload();
    await expect(detail.getByRole("heading", { name: "Publish operator guide" })).toBeVisible();
    await expect(page.getByTestId("desktop-product-navigation").getByLabel("Delivery")).toHaveAttribute(
      "aria-current",
      "page",
    );

    await page.getByRole("button", { name: "Dismiss flyout" }).click();
    await expect(page.getByRole("button", { name: "Current delivery", exact: true })).toBeFocused();
    const historyResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "GET" && new URL(response.url()).pathname === "/api/work-items/completed",
    );
    await page.getByRole("button", { name: "Change history" }).click();
    expect((await historyResponse).status()).toBe(200);
    await expect(page.getByTestId("completed-change-record")).toHaveCount(2);
    await expect(page.getByText("Alpha delivery", { exact: true })).toBeVisible();
    const receiptRecord = page.getByTestId("completed-change-record").filter({ hasText: "Beta search" });
    await receiptRecord.getByRole("button", { name: "Inspect" }).click();
    const completionDetail = page.getByTestId("completed-change-detail");
    await expect(completionDetail).toContainText("Completion receipt");
    await expect(completionDetail).toContainText("Finalized Change head");
    await expect(completionDetail).toContainText("Accepted merge commit");
    await expect(completionDetail).toContainText("#42");
    await expectNoHorizontalOverflow(page);
    await page.screenshot({
      path: testInfo.outputPath("delivery-completed-history.png"),
      fullPage: true,
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await expect(completionDetail).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.screenshot({
      path: testInfo.outputPath("delivery-completed-history-mobile.png"),
      fullPage: true,
    });
  });

  test("closing detail does not leave a history entry that reopens it", async ({ page }) => {
    await page.goto("/delivery");

    const inspected = await inspect(page, "Build operator controls");
    await page.getByRole("button", { name: "Dismiss flyout" }).click();
    await expect(page.getByTestId("work-item-detail")).not.toBeVisible();
    await expect(page).toHaveURL(/\/delivery$/);

    await page.goBack();
    await expect(page).toHaveURL(/\/delivery$/);
    await expect(page.getByTestId("work-item-detail")).not.toBeVisible();
    await expect(inspected.trigger).toBeVisible();
  });

  test("browser Back from detail restores the originating trigger focus", async ({ page }) => {
    await page.goto("/delivery");

    const inspected = await inspect(page, "Build operator controls");
    await page.goBack();
    await expect(page).toHaveURL(/\/delivery$/);
    await expect(page.getByTestId("work-item-detail")).not.toBeVisible();
    await expect(inspected.trigger).toBeFocused();
  });

  test("refreshes current delivery immediately after returning from completed history", async ({ page }) => {
    let refreshPortfolio = false;
    await page.route("**/api/work-items", async (route) => {
      const response = await route.fetch();
      if (!refreshPortfolio) {
        await route.fulfill({ response });
        return;
      }
      const payload = (await response.json()) as {
        groups: Array<Record<string, unknown>>;
      };
      const [firstGroup, ...remainingGroups] = payload.groups;
      await route.fulfill({
        response,
        body: JSON.stringify({
          ...payload,
          groups: firstGroup ? [{ ...firstGroup, title: "Refreshed portfolio" }, ...remainingGroups] : payload.groups,
        }),
      });
    });

    try {
      await page.goto("/delivery");
      await expect(page.getByText("Work portfolio E2E", { exact: true })).toBeVisible();
      await page.getByRole("button", { name: "Change history" }).click();
      await expect(page.getByTestId("completed-history-workspace")).toBeVisible();

      refreshPortfolio = true;
      await page.getByRole("button", { name: "Current delivery" }).click();
      await expect(page.getByText("Refreshed portfolio", { exact: true })).toBeVisible({ timeout: 1_000 });
    } finally {
      await page.unroute("**/api/work-items");
    }
  });

  test("completed history detail dismisses on Escape and restores record focus", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 760 });
    await page.goto("/delivery");

    const historyResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "GET" && new URL(response.url()).pathname === "/api/work-items/completed",
    );
    await page.getByRole("button", { name: "Change history" }).click();
    expect((await historyResponse).status()).toBe(200);
    const receiptRecord = page.getByTestId("completed-change-record").filter({ hasText: "Beta search" });
    await expect(receiptRecord).toBeVisible();
    const trigger = receiptRecord.getByRole("button", { name: "Inspect" });
    await trigger.click();

    const completionDetail = page.getByTestId("completed-change-detail");
    await expect(completionDetail).toContainText("Completion receipt");
    await completionDetail.getByRole("button", { name: "Close" }).focus();
    await page.keyboard.press("Escape");
    await expect(completionDetail).not.toBeVisible();
    await expect(trigger).toBeFocused();
  });

  test("browser Back from completed history detail restores record focus", async ({ page }) => {
    await page.goto("/delivery");
    await page.getByRole("button", { name: "Change history" }).click();

    const receiptRecord = page.getByTestId("completed-change-record").filter({ hasText: "Beta search" });
    const trigger = receiptRecord.getByRole("button", { name: "Inspect" });
    await trigger.click();

    const completionDetail = page.getByTestId("completed-change-detail");
    await expect(completionDetail).toContainText("Completion receipt");
    await expect(page).toHaveURL(/\/delivery\/history\/[^/]+\/[^/]+$/);

    await page.goBack();
    await expect(completionDetail).not.toBeVisible();
    await expect(trigger).toBeFocused();
    await expect(page.getByTestId("completed-history-workspace")).toBeVisible();
  });

  test("completed history detail survives reload and restores workspace focus", async ({ page }) => {
    await page.goto("/delivery");
    await page.getByRole("button", { name: "Change history" }).click();

    const receiptRecord = page.getByTestId("completed-change-record").filter({ hasText: "Beta search" });
    await receiptRecord.getByRole("button", { name: "Inspect" }).click();

    const completionDetail = page.getByTestId("completed-change-detail");
    await expect(completionDetail).toContainText("Completion receipt");
    await expect(page).toHaveURL(/\/delivery\/history\/[^/]+\/[^/]+$/);

    await page.reload();
    await expect(page).toHaveURL(/\/delivery\/history\/[^/]+\/[^/]+$/);
    await expect(completionDetail).toContainText("Finalized Change head");

    await completionDetail.getByRole("button", { name: "Close" }).click();
    await expect(completionDetail).not.toBeVisible();
    await expect(page.getByTestId("completed-history-workspace")).toBeFocused();
  });

  test("completed history detail closes with its Close button and restores record focus", async ({ page }) => {
    await page.goto("/delivery");
    await page.getByRole("button", { name: "Change history" }).click();

    const receiptRecord = page.getByTestId("completed-change-record").filter({ hasText: "Beta search" });
    const trigger = receiptRecord.getByRole("button", { name: "Inspect" });
    await trigger.click();

    const completionDetail = page.getByTestId("completed-change-detail");
    await expect(completionDetail).toContainText("Completion receipt");
    await completionDetail.getByRole("button", { name: "Close" }).click();
    await expect(completionDetail).not.toBeVisible();
    await expect(trigger).toBeFocused();
  });

  test("completed history detail closes from the backdrop and restores record focus", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 760 });
    await page.goto("/delivery");
    await page.getByRole("button", { name: "Change history" }).click();

    const receiptRecord = page.getByTestId("completed-change-record").filter({ hasText: "Beta search" });
    const trigger = receiptRecord.getByRole("button", { name: "Inspect" });
    await trigger.click();

    const completionDetail = page.getByTestId("completed-change-detail");
    await expect(completionDetail).toContainText("Completion receipt");
    const backdropPoint = await page
      .locator("p-flyout")
      .last()
      .evaluate((element) => {
        const dialog = element.shadowRoot?.querySelector("dialog");
        if (!dialog) return null;
        const box = dialog.getBoundingClientRect();
        return { x: box.left + 16, y: box.top + box.height / 2 };
      });
    expect(backdropPoint).not.toBeNull();
    const point = requirePresent(backdropPoint);
    await page.mouse.click(point.x, point.y);
    await expect(completionDetail).not.toBeVisible();
    await expect(trigger).toBeFocused();
  });

  test("completed history restores focus when a pending search replaces the open detail trigger", async ({ page }) => {
    let releaseSearch: (() => void) | undefined;
    const searchBlocked = new Promise<void>((resolve) => {
      releaseSearch = resolve;
    });
    await page.route("**/api/work-items/completed/search**", async (route) => {
      await searchBlocked;
      await route.continue();
    });

    try {
      await page.goto("/delivery");
      await page.getByRole("button", { name: "Change history" }).click();
      await expect(page.getByTestId("completed-change-record")).toHaveCount(2);

      const searchInput = page.locator('p-input-search[name="completed-history-search"]').locator("input");
      await searchInput.fill("Beta");
      await expect(page.getByTestId("completed-history-stale-status")).toBeVisible();

      const receiptRecord = page.getByTestId("completed-change-record").filter({ hasText: "Alpha delivery" });
      const trigger = receiptRecord.getByRole("button", { name: "Inspect" });
      await trigger.click();
      await expect(page.getByTestId("completed-change-detail")).toContainText("Completion receipt");

      releaseSearch?.();
      await expect(page.getByTestId("completed-change-record")).toHaveCount(1);
      await expect(page.getByTestId("completed-change-record").filter({ hasText: "Beta search" })).toBeVisible();
      await expect(page.getByTestId("completed-change-detail")).not.toBeVisible();
      await expect(page.getByTestId("completed-history-workspace")).toBeFocused();
    } finally {
      releaseSearch?.();
      await page.unroute("**/api/work-items/completed/search**");
    }
  });

  test("completed history focuses its workspace when detail closes during a pending search", async ({ page }) => {
    let releaseSearch: (() => void) | undefined;
    const searchBlocked = new Promise<void>((resolve) => {
      releaseSearch = resolve;
    });
    await page.route("**/api/work-items/completed/search**", async (route) => {
      await searchBlocked;
      await route.continue();
    });

    try {
      await page.goto("/delivery");
      await page.getByRole("button", { name: "Change history" }).click();
      await expect(page.getByTestId("completed-change-record")).toHaveCount(2);

      const searchInput = page.locator('p-input-search[name="completed-history-search"]').locator("input");
      await searchInput.fill("Beta");
      await expect(page.getByTestId("completed-history-stale-status")).toBeVisible();

      const receiptRecord = page.getByTestId("completed-change-record").filter({ hasText: "Alpha delivery" });
      await receiptRecord.getByRole("button", { name: "Inspect" }).click();
      const completionDetail = page.getByTestId("completed-change-detail");
      await expect(completionDetail).toContainText("Completion receipt");

      await completionDetail.getByRole("button", { name: "Close" }).click();
      await expect(completionDetail).not.toBeVisible();
      await expect(page.getByTestId("completed-history-workspace")).toBeFocused();

      releaseSearch?.();
      await expect(page.getByTestId("completed-change-record")).toHaveCount(1);
      await expect(page.getByTestId("completed-history-workspace")).toBeFocused();
    } finally {
      releaseSearch?.();
      await page.unroute("**/api/work-items/completed/search**");
    }
  });

  test("completed history search remains editable while results are pending", async ({ page }) => {
    let releaseSearch: (() => void) | undefined;
    const searchBlocked = new Promise<void>((resolve) => {
      releaseSearch = resolve;
    });
    await page.route("**/api/work-items/completed/search**", async (route) => {
      await searchBlocked;
      await route.continue();
    });

    try {
      await page.goto("/delivery");
      await page.getByRole("button", { name: "Change history" }).click();
      await expect(page.getByTestId("completed-change-record")).toHaveCount(2);

      const search = page.locator('p-input-search[name="completed-history-search"]');
      const input = search.locator("input");
      await input.fill("Beta");
      await expect(page.getByTestId("completed-history-stale-status")).toBeVisible();
      await expect(page.getByTestId("completed-history-results")).toHaveAttribute("aria-busy", "true");

      await input.fill("Alpha");
      await expect(input).toHaveValue("Alpha");
      releaseSearch?.();

      await expect(page.getByTestId("completed-change-record")).toHaveCount(1);
      await expect(page.getByText("Alpha delivery", { exact: true })).toBeVisible();
      await expect(page.getByText("Beta search", { exact: true })).not.toBeVisible();
    } finally {
      releaseSearch?.();
      await page.unroute("**/api/work-items/completed/search**");
    }
  });

  test("automatically removed Work Item routes to history and restores view focus", async ({ page }) => {
    let removeSelectedChange = false;
    await page.route("**/api/work-items", async (route) => {
      const response = await route.fetch();
      if (!removeSelectedChange) {
        await route.fulfill({ response });
        return;
      }
      const payload = (await response.json()) as {
        groups: Array<{ change_id: string }>;
      };
      await route.fulfill({
        response,
        body: JSON.stringify({
          ...payload,
          groups: payload.groups.filter((group) => group.change_id !== "work-e2e"),
        }),
      });
    });

    try {
      await page.goto("/delivery");
      await inspect(page, "Build operator controls");
      const historyView = page.getByRole("button", { name: "Change history" });
      removeSelectedChange = true;
      await page.waitForResponse(
        (response) => response.request().method() === "GET" && new URL(response.url()).pathname === "/api/work-items",
      );
      await expect(page.getByTestId("completed-history-workspace")).toBeVisible();
      await expect(historyView).toBeFocused();
    } finally {
      await page.unroute("**/api/work-items");
    }
  });

  test("automatically closes removed Design detail and restores current view focus", async ({ page }) => {
    let removeDesign = false;
    await page.route("**/api/work-items", async (route) => {
      const response = await route.fetch();
      if (!removeDesign) {
        await route.fulfill({ response });
        return;
      }
      const payload = (await response.json()) as {
        operating: { statuses: Array<{ change_id: string }> };
      };
      await route.fulfill({
        response,
        body: JSON.stringify({
          ...payload,
          operating: {
            ...payload.operating,
            statuses: payload.operating.statuses.filter((status) => status.change_id !== "design-operations-roadmap"),
          },
        }),
      });
    });

    try {
      await page.goto("/delivery");
      const designTrigger = page
        .getByTestId("design-work-section")
        .getByRole("link", { name: "Design Operations Roadmap" });
      await designTrigger.click();
      await expect(page.getByTestId("design-work-detail")).toBeVisible();

      removeDesign = true;
      await page.waitForResponse(
        (response) => response.request().method() === "GET" && new URL(response.url()).pathname === "/api/work-items",
      );
      await expect(page.getByTestId("design-work-detail")).not.toBeVisible();
      await expect(page.getByRole("button", { name: "Current delivery" })).toBeFocused();
    } finally {
      await page.unroute("**/api/work-items");
    }
  });

  test("copies the continuation prompt and pauses then resumes a quiescent Change", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
    await page.goto("/delivery");

    const row = (await visibleRows(page)).filter({ hasText: "Build operator controls" });
    await expect(row.getByText("Ready for next step", { exact: true })).toBeVisible();
    const copy = row.getByRole("button", { name: "Copy continuation prompt" });
    await expect(copy).toHaveAccessibleDescription("Run it in Copilot Chat. Copying does not start an agent.");
    await copy.click();
    await expect
      .poll(() => page.evaluate(() => navigator.clipboard.readText()))
      .toMatch(/^\/continue-change work-e2e /);
    await expect(page).toHaveURL(/\/delivery$/);
    const copied = await page.evaluate(() => navigator.clipboard.readText());
    const table = page.getByTestId("work-portfolio-table");
    await expect(table).not.toContainText(/\bStart\b/);
    await expect(table).not.toContainText(/\bWorking\b/);

    const { detail, trigger } = await inspect(page, "Build operator controls");
    await expect(detail.getByTestId("readiness-prompt")).toHaveText(copied);
    await expect(detail.getByTestId("readiness-progress")).toHaveText("Ready for next step");
    await expect(detail.getByTestId("change-pause-work-e2e").getByText("Pause", { exact: true })).toBeVisible();
    const requirements = detail.getByRole("button", { name: "Change requirements" });
    await expect(requirements).toHaveAccessibleDescription(
      /run it in Copilot Chat\. Copying does not start an agent\.$/,
    );
    await requirements.click();
    await expect
      .poll(() => page.evaluate(() => navigator.clipboard.readText()))
      .toBe("/design work-e2e Change requirements:");
    await returnToPortfolio(page, trigger);

    const control = page.getByTestId("change-pause-publication-e2e");
    const progress = page.getByTestId("change-progress-publication-e2e");
    await expect(progress).toHaveText("Ready for next step");
    await control.getByText("Pause", { exact: true }).click();
    await inputValue(control.locator('p-input-text[name="change-pause-reason-publication-e2e"]'), "Hold for review");
    await control.getByText("Confirm pause", { exact: true }).click();
    await expect(progress).toHaveText("Paused");
    await control.getByText("Resume", { exact: true }).click();
    await expect(progress).toHaveText("Ready for next step");
    await expect(page.getByLabel("Change publication for Publication release")).toContainText("Ready for finalization");
  });

  test("unknown paths render the global Not Found view", async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/delivery/work-e2e");

    await expect(page.getByTestId("not-found-view")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath("cockpit-not-found.png"),
      fullPage: true,
    });
  });
});

const STUCK_WORKER_ORIGIN = "http://127.0.0.1:4176";
const WORKER_QUIET_PERIOD_MS = 30_000;

type ClaimDetail = {
  item: {
    active_claim: { attempt_id: string; claim_id: string; started_at: string; continuation: boolean } | null;
    pause_unavailable_reason?: string | null;
    card: {
      readiness: {
        status: string;
        reason_code: string;
        retry_history?: Array<{ status: string; failure_code: string | null }>;
      } | null;
    };
  };
};

async function stuckWorkerDetail(page: Page, changeId: string): Promise<ClaimDetail> {
  const response = await page.request.get(
    `${STUCK_WORKER_ORIGIN}/api/changes/${changeId}/work-items/${encodeURIComponent("outcome:OUT-001")}`,
  );
  expect(response.status()).toBe(200);
  return (await response.json()) as ClaimDetail;
}

async function openReleaseConfirmation(page: Page, changeId: string, title: string): Promise<Locator> {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${STUCK_WORKER_ORIGIN}/delivery/${changeId}/${encodeURIComponent("outcome:OUT-001")}`);
  const detail = page.getByTestId("work-item-detail");
  await expect(detail.getByRole("heading", { name: `Plan ${title}`, exact: true })).toBeVisible();
  await expect(detail.getByRole("heading", { name: "Active claim" })).toBeVisible();
  await expect(detail.getByTestId("claim-continuation-custody")).toBeVisible();
  await detail.getByRole("button", { name: "Release stuck worker" }).click();
  const modal = page.locator("p-modal").filter({ hasText: "Use this only for a worker whose chat was stopped" });
  await expect(modal).toBeVisible();
  await expect
    .poll(() => modal.evaluate((element) => element.shadowRoot?.querySelector("dialog")?.open ?? false))
    .toBe(true);
  const confirm = modal.getByRole("button", { name: "Confirm release" });
  await confirm.focus();
  await expect(confirm).toBeFocused();
  return modal;
}

test.describe("assembled stuck-worker release", () => {
  test.describe.configure({ mode: "serial" });

  test("refuses release while the worker's worktree is still changing", async ({ page }) => {
    const before = await stuckWorkerDetail(page, "stuck-active-e2e");
    const claim = requirePresent(before.item.active_claim);
    const modal = await openReleaseConfirmation(page, "stuck-active-e2e", "Active worker");
    await expect(modal).toContainText(claim.attempt_id);

    const releaseResponse = page.waitForResponse(
      (response) => response.request().method() === "POST" && response.url().endsWith("/workers/release-stuck"),
    );
    await modal.getByRole("button", { name: "Confirm release" }).click();
    expect((await releaseResponse).status()).toBe(409);

    const feedback = modal.getByRole("status").filter({ hasText: "ERR_DELIVERY_WORKER_ACTIVE" });
    await expect(feedback).toContainText("the worker may still be active. Nothing was changed.");
    const retryAfter = requirePresent(await feedback.getByTestId("worker-active-retry-after").getAttribute("datetime"));
    expect(new Date(retryAfter).getTime()).toBeGreaterThan(Date.now());
    expect(new Date(retryAfter).getTime()).toBeLessThanOrEqual(Date.now() + WORKER_QUIET_PERIOD_MS + 5_000);
    await expect(modal).toBeVisible();

    const after = await stuckWorkerDetail(page, "stuck-active-e2e");
    expect(after.item.active_claim).toEqual(claim);
    expect(after.item.card.readiness).toEqual(before.item.card.readiness);
    await modal.getByRole("button", { name: "Cancel" }).click();
    await expect(modal).not.toBeVisible();
    await expect(page.getByTestId("work-item-detail").getByRole("heading", { name: "Active claim" })).toBeVisible();
  });

  test("refuses release while a leftover process still uses the worker's worktree", async ({ page }) => {
    test.setTimeout(WORKER_QUIET_PERIOD_MS + 90_000);
    const before = await stuckWorkerDetail(page, "stuck-busy-e2e");
    const claim = requirePresent(before.item.active_claim);
    // Outlast the write guard so only the live process can explain the refusal.
    const quietAt = new Date(claim.started_at).getTime() + WORKER_QUIET_PERIOD_MS + 5_000;
    await page.waitForTimeout(Math.max(quietAt - Date.now(), 0));
    const modal = await openReleaseConfirmation(page, "stuck-busy-e2e", "Busy worker");

    const releaseResponse = page.waitForResponse(
      (response) => response.request().method() === "POST" && response.url().endsWith("/workers/release-stuck"),
    );
    await modal.getByRole("button", { name: "Confirm release" }).click();
    const response = await releaseResponse;
    expect(response.status()).toBe(409);
    const body = (await response.json()) as Record<string, unknown>;
    expect(body.code).toBe("ERR_DELIVERY_WORKER_ACTIVE");
    expect(body).not.toHaveProperty("retry_after");
    expect(body.detail).toContain("still active in the worker's worktree");

    const feedback = modal.getByRole("status").filter({ hasText: "ERR_DELIVERY_WORKER_ACTIVE" });
    await expect(feedback).toContainText("(node) is still active in the worker's worktree");
    await expect(feedback).toContainText("Custody, files and retry accounting are unchanged.");
    await expect(feedback.getByTestId("worker-active-retry-after")).toHaveCount(0);

    const after = await stuckWorkerDetail(page, "stuck-busy-e2e");
    expect(after.item.active_claim).toEqual(claim);
    expect(after.item.card.readiness).toEqual(before.item.card.readiness);
    await modal.getByRole("button", { name: "Cancel" }).click();
    await expect(modal).not.toBeVisible();
  });

  test("releases a stopped worker once its worktree is quiet", async ({ page }) => {
    test.setTimeout(WORKER_QUIET_PERIOD_MS + 90_000);
    const before = await stuckWorkerDetail(page, "stuck-quiet-e2e");
    const claim = requirePresent(before.item.active_claim);
    expect(claim.continuation).toBe(true);
    expect(before.item.card.readiness?.status).toBe("running");
    // Fixture seeding is the worktree's last write; ctime cannot be backdated, so wait out the real quiet period.
    const quietAt = new Date(claim.started_at).getTime() + WORKER_QUIET_PERIOD_MS + 10_000;
    await page.waitForTimeout(Math.max(quietAt - Date.now(), 0));

    const modal = await openReleaseConfirmation(page, "stuck-quiet-e2e", "Quiet stopped worker");
    await expect(modal).toContainText(claim.claim_id);
    const releaseResponse = page.waitForResponse(
      (response) => response.request().method() === "POST" && response.url().endsWith("/workers/release-stuck"),
    );
    await modal.getByRole("button", { name: "Confirm release" }).click();
    expect((await releaseResponse).status()).toBe(200);

    const detail = page.getByTestId("work-item-detail");
    await expect(modal).not.toBeVisible();
    await expect(
      detail.getByText("Stuck worker released. The attempt was recorded as failed; its work is preserved."),
    ).toBeVisible();
    await expect(detail.getByRole("heading", { name: "Active claim" })).toHaveCount(0);
    await expect(detail.getByRole("button", { name: "Release stuck worker" })).toHaveCount(0);
    await expect(detail.getByTestId("readiness-status")).not.toHaveText("Running");
    await expect(detail.getByTestId("readiness-retry-history")).toContainText("original failed worker-released-stuck");

    const after = await stuckWorkerDetail(page, "stuck-quiet-e2e");
    expect(after.item.active_claim).toBeNull();
    expect(after.item.card.readiness?.status).not.toBe("running");
    expect(after.item.card.readiness?.retry_history).toEqual([
      expect.objectContaining({ status: "failed", failure_code: "worker-released-stuck" }),
    ]);
  });

  test("records Pause requested while a worker holds custody and Resume clears it", async ({ page }) => {
    const before = await stuckWorkerDetail(page, "stuck-busy-e2e");
    const claim = requirePresent(before.item.active_claim);
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(`${STUCK_WORKER_ORIGIN}/delivery/stuck-busy-e2e/${encodeURIComponent("outcome:OUT-001")}`);
    const detail = page.getByTestId("work-item-detail");
    await expect(detail.getByRole("heading", { name: "Active claim" })).toBeVisible();
    const control = detail.getByTestId("change-pause-stuck-busy-e2e");

    await control.getByText("Pause", { exact: true }).click();
    await inputValue(control.locator('p-input-text[name="change-pause-reason"]'), "Hold for review");
    const pauseResponse = page.waitForResponse(
      (response) => response.request().method() === "POST" && response.url().endsWith("/defer"),
    );
    await control.getByText("Confirm pause", { exact: true }).click();
    expect((await pauseResponse).status()).toBe(200);

    await expect(control.getByTestId("pause-requested-stuck-busy-e2e")).toHaveText("Pause requested");
    await expect(detail.getByRole("heading", { name: "Active claim" })).toBeVisible();
    const requested = await stuckWorkerDetail(page, "stuck-busy-e2e");
    expect(requested.item.active_claim).toEqual(claim);
    expect(requested.item.pause_unavailable_reason).toBe("pause-requested");

    await control.getByText("Resume", { exact: true }).click();
    await expect(control.getByTestId("pause-requested-stuck-busy-e2e")).toHaveCount(0);
    await expect(control.getByText("Pause", { exact: true })).toBeVisible();
    const resumed = await stuckWorkerDetail(page, "stuck-busy-e2e");
    expect(resumed.item.active_claim).toEqual(claim);
    expect(resumed.item.pause_unavailable_reason).toBeNull();
  });
});

const MERGE_ORIGIN = "http://127.0.0.1:4177";
// The stack seeds this fixture through the default loader with this fake `gh` first on PATH.
const FAKE_GH_STATE = join(tmpdir(), "owlbear-work-merge-4177", "fake-gh.json");
const FAKE_GH = resolve(process.cwd(), "e2e/support/fake-gh.mjs");

type FakeGhCall = { method: string; endpoint: string; body: Record<string, unknown> | null };
type FakeGhState = { pulls: Record<string, { number: number; head: string }> };

function fakeGh(...arguments_: string[]): void {
  execFileSync(process.execPath, [FAKE_GH, ...arguments_], {
    env: { ...process.env, OWLBEAR_FAKE_GH_STATE: FAKE_GH_STATE },
  });
}

function pullNumber(changeId: string): number {
  const state = JSON.parse(readFileSync(FAKE_GH_STATE, "utf8")) as FakeGhState;
  return requirePresent(Object.values(state.pulls).find((pull) => pull.head === `owlbear/change/${changeId}`)).number;
}

function mergeRequests(changeId: string): FakeGhCall[] {
  const endpoint = `/pulls/${pullNumber(changeId)}/merge-async`;
  return readFileSync(`${FAKE_GH_STATE}.calls.jsonl`, "utf8")
    .trim()
    .split("\n")
    .map((line) => JSON.parse(line) as FakeGhCall)
    .filter((call) => call.method === "PUT" && call.endpoint.endsWith(endpoint));
}

async function openMergeChange(page: Page, changeId: string): Promise<Locator> {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${MERGE_ORIGIN}/delivery/${changeId}/publication`);
  const detail = page.getByTestId("work-item-detail");
  await expect(detail.getByTestId("delivery-readiness")).toBeVisible();
  return detail;
}

async function openApproveMerge(page: Page, detail: Locator): Promise<Locator> {
  // Readiness caches provider facts for 15 seconds; detail polling shows the current offer after that.
  await expect(detail.getByTestId("merge-offer")).toBeVisible({ timeout: 30_000 });
  await detail.getByRole("button", { name: "Approve merge" }).click();
  const modal = page.locator("p-modal").filter({ hasText: "Delivery cannot undo the merge." });
  await expect(modal).toBeVisible();
  return modal;
}

function mergeResponse(page: Page, path: string) {
  return page.waitForResponse((response) => response.request().method() === "POST" && response.url().endsWith(path));
}

test.describe("assembled merge approval", () => {
  test.describe.configure({ mode: "serial" });

  test("refuses an offer that changed while the dialog was open and sends no merge request", async ({ page }) => {
    const detail = await openMergeChange(page, "merge-stale-e2e");
    const modal = await openApproveMerge(page, detail);
    fakeGh("__move-head", String(pullNumber("merge-stale-e2e")), "f".repeat(40));

    const approval = mergeResponse(page, "/approve-merge");
    await modal.getByRole("button", { name: "Approve merge" }).click();
    expect((await approval).status()).toBe(409);

    await expect(modal.getByRole("alert")).toContainText("ERR_DELIVERY_MERGE_OFFER_STALE");
    await expect(modal.getByRole("alert")).toContainText("nothing was merged");
    expect(mergeRequests("merge-stale-e2e")).toEqual([]);
    await modal.getByRole("button", { name: "Cancel" }).click();
    await expect(modal).not.toBeVisible();
  });

  test("shows an unknown merge with its PR link and checks again only when asked", async ({ page }) => {
    const detail = await openMergeChange(page, "merge-unknown-e2e");
    const number = pullNumber("merge-unknown-e2e");
    await expect(detail).toContainText("GitHub has not confirmed this merge.");
    await expect(detail.locator('[data-readiness-reason="merge-response-unknown"]')).toBeAttached();
    await expect(detail.getByTestId("merge-attempt").getByRole("link")).toHaveAttribute(
      "href",
      `https://github.com/example/project/pull/${number}`,
    );
    await expect(detail.getByRole("button", { name: "Approve merge" })).toHaveCount(0);
    await expect(
      detail.getByTestId("change-pause-merge-unknown-e2e").getByText("Pause", { exact: true }),
    ).toBeVisible();
    expect(mergeRequests("merge-unknown-e2e")).toHaveLength(1);

    const stillUnknown = mergeResponse(page, "/acceptance/observe");
    await detail.getByRole("button", { name: "Check again" }).click();
    expect((await stillUnknown).status()).toBe(409);
    await expect(detail).toContainText("GitHub has not confirmed this merge.");
    await expect(detail.locator('[data-readiness-reason="merge-response-unknown"]')).toBeAttached();

    fakeGh("__merge", String(number));
    // Cockpit's background acceptance reconciliation can briefly hold the Change lock; the user clicks again.
    const refusals: string[] = [];
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const merged = mergeResponse(page, "/acceptance/observe");
      await detail.getByRole("button", { name: "Check again" }).click();
      const observed = await merged;
      if (observed.status() === 200) break;
      refusals.push(await observed.text());
    }
    expect(refusals.length, refusals.join("\n")).toBeLessThan(3);

    const completed = await page.request.get(`${MERGE_ORIGIN}/api/work-items/completed/merge-unknown-e2e`);
    expect(completed.status()).toBe(200);
    expect(mergeRequests("merge-unknown-e2e")).toHaveLength(1);
    fakeGh("__restore-target");
  });

  test("abandons a Change whose merge is unknown without another merge request", async ({ page }) => {
    const detail = await openMergeChange(page, "merge-abandon-e2e");
    await expect(detail).toContainText("GitHub has not confirmed this merge.");
    await expect(detail.locator('[data-readiness-reason="merge-response-unknown"]')).toBeAttached();

    await detail.getByText("Change lifecycle").click();
    await inputValue(detail.locator('p-input-text[name="change-disposition-reason"]'), "Merge outcome unknown");
    await detail.getByRole("button", { name: "Abandon Change" }).click();
    const modal = page.locator("p-modal").filter({ hasText: "Confirm Change abandonment" });
    const abandoned = mergeResponse(page, "/abandon");
    await modal.getByRole("button", { name: "Confirm abandon Change" }).click();
    expect((await abandoned).status()).toBe(200);

    expect(mergeRequests("merge-abandon-e2e")).toHaveLength(1);
  });

  test("approves the exact offer once in the dialog and Delivery records completion", async ({ page }) => {
    const detail = await openMergeChange(page, "merge-approve-e2e");
    const cancelled = await openApproveMerge(page, detail);
    await cancelled.getByRole("button", { name: "Cancel" }).click();
    await expect(cancelled).not.toBeVisible();
    expect(mergeRequests("merge-approve-e2e")).toEqual([]);

    const modal = await openApproveMerge(page, detail);
    await expect(modal.getByTestId("merge-approval-offer")).toContainText("merge");
    // Background merge observation of the other Changes can publish state mid-approval; the user approves again.
    let response = await Promise.all([
      mergeResponse(page, "/approve-merge"),
      modal.getByRole("button", { name: "Approve merge" }).click(),
    ]).then(([approved]) => approved);
    for (let attempt = 0; attempt < 2 && response.status() === 409; attempt += 1) {
      expect(await response.text()).toContain("ERR_DELIVERY_STATE_CONFLICT");
      expect(mergeRequests("merge-approve-e2e")).toEqual([]);
      response = await Promise.all([
        mergeResponse(page, "/approve-merge"),
        modal.getByRole("button", { name: "Approve merge" }).click(),
      ]).then(([approved]) => approved);
    }
    expect(response.status()).toBe(200);
    const result = (await response.json()) as { state: string; completion_id: string | null };
    expect(result.state).toBe("merged");
    expect(result.completion_id).not.toBeNull();

    const [request] = mergeRequests("merge-approve-e2e");
    expect(mergeRequests("merge-approve-e2e")).toHaveLength(1);
    expect(request.body).toEqual({
      sha: expect.stringMatching(/^[0-9a-f]{40}$/),
      merge_method: "merge",
      merge_action: "direct_merge",
      bypass_rules: false,
    });
    const completed = await page.request.get(`${MERGE_ORIGIN}/api/work-items/completed/merge-approve-e2e`);
    expect(completed.status()).toBe(200);
  });
});
