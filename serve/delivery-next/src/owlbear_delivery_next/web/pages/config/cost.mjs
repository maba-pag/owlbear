// Settings' cost arrows (D-01M621PC80RKPA2XJR4DZD1YKV, D-01M68ZZZE6707CQ2D029TE3T2B): an option is dearer than
// another when any rate both state is higher, so two options that cross are each dearer. Its arrows count the
// distinct priced options it is dearer than; an option without rates gets none.
export const RATES = ["input", "output", "cache", "cache_write", "cache_write_1h"];

export function dearer(a, b) {
  return RATES.some((k) => a[k] != null && b[k] != null && a[k] > b[k]);
}

function same(a, b) {
  return RATES.every((k) => (a[k] ?? null) === (b[k] ?? null));
}

export function levels(sets) {
  const known = sets.filter((s, i) => s && sets.findIndex((t) => t && same(s, t)) === i);
  return sets.map((s) => (s ? known.filter((t) => dearer(s, t)).length : 0));
}

export function arrows(n) {
  return n ? `\u00a0${"\u2191".repeat(n)}` : "";
}
