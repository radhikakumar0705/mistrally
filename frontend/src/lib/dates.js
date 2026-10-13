const DAY_MS = 24 * 60 * 60 * 1000;

// The API returns naive UTC timestamps ("2026-10-13T11:17:35"); treat them as UTC
export const parseServerDate = (value) => {
  if (!value) return null;
  const hasZone = /[zZ]|[+-]\d\d:?\d\d$/.test(value);
  return new Date(hasZone ? value : `${value}Z`);
};

const startOfDay = (date) => new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();

/** Group items like a chat sidebar: Today, Yesterday, Previous 7 days, Previous 30 days, Older. */
export function groupByDate(items, getDate, now = new Date()) {
  const today = startOfDay(now);
  const buckets = [
    { label: "Today", from: today },
    { label: "Yesterday", from: today - DAY_MS },
    { label: "Previous 7 days", from: today - 7 * DAY_MS },
    { label: "Previous 30 days", from: today - 30 * DAY_MS },
    { label: "Older", from: -Infinity },
  ].map((bucket) => ({ ...bucket, items: [] }));

  for (const item of items) {
    const time = parseServerDate(getDate(item))?.getTime() ?? 0;
    buckets.find((bucket) => time >= bucket.from).items.push(item);
  }
  return buckets.filter((bucket) => bucket.items.length).map(({ label, items }) => ({ label, items }));
}
