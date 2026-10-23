// Ordering and URL grouping affect presentation only; original records stay intact.
export function sortDetections(records, order = "newest") {
  return records.map((record, index) => ({ record, index,
    time: Date.parse(record.observed_at || record._detail?.observed_at || "") || 0,
  })).sort((a, b) => (order === "oldest" ? 1 : -1) * (a.time - b.time || a.index - b.index))
    .map(item => item.record);
}
