const AREA_NAMES = {
  rooms: "Room",
  labs: "Lab",
  courses: "Course section",
  faculty: "Faculty member",
  patterns: "Class pattern",
  time_slots: "Time slots",
  settings: "Settings",
};

/**
 * Where an issue from the API is, in words: "Faculty member 2 · minimum_credits".
 * Pass `labels` (for example `{ courses: ["CMSC 140.01", ...] }`) to use names instead
 * of numbers.
 */
export function describeIssueLocation(issue, labels = {}) {
  if (!issue?.area) return issue?.field ?? "";
  const parts = [AREA_NAMES[issue.area] ?? issue.area];
  if (issue.index != null) {
    const name = labels[issue.area]?.[issue.index];
    parts[0] = name ? `${parts[0]} ${name}` : `${parts[0]} ${issue.index + 1}`;
  }
  if (issue.field) parts.push(issue.field);
  return parts.join(" · ");
}

/** The issues for one field of one item, for showing next to that field. */
export function issuesFor(issues, { area, index, field }) {
  return (issues ?? []).filter(
    (issue) =>
      issue.area === area &&
      (index === undefined || issue.index === index) &&
      (field === undefined || issue.field === field || issue.field?.startsWith(`${field}.`)),
  );
}
