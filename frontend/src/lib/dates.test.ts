import { describe, expect, it } from "vitest";
import { groupByDate, parseServerDate } from "./dates";

describe("dates", () => {
  it("treats naive server timestamps as UTC", () => {
    expect(parseServerDate("2026-10-13T11:00:00")?.toISOString()).toBe("2026-10-13T11:00:00.000Z");
    expect(parseServerDate(null)).toBeNull();
  });

  it("groups items into sidebar buckets", () => {
    const now = new Date(2026, 9, 13, 15, 0, 0);
    const at = (daysAgo: number) => new Date(now.getTime() - daysAgo * 86400000).toISOString();
    const items = [
      { id: 1, t: at(0) },
      { id: 2, t: at(1) },
      { id: 3, t: at(3) },
      { id: 4, t: at(20) },
      { id: 5, t: at(90) },
    ];
    const groups = groupByDate(items, (i) => i.t, now);
    expect(groups.map((g) => [g.label, g.items.map((i) => i.id)])).toEqual([
      ["Today", [1]],
      ["Yesterday", [2]],
      ["Previous 7 days", [3]],
      ["Previous 30 days", [4]],
      ["Older", [5]],
    ]);
  });
});
