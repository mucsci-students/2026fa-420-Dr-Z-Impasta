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

/**
 * The issues from a rejected Save, sorted for a form that edits one item. `fields` are the
 * fields the form shows; `index` is undefined for a new item or an area without items.
 *
 * - `errorFor(field, exact)`: the messages for that field and its sub-fields (only the field
 *   itself if `exact`), joined, or undefined if there are none. Use it as a Field's `error`.
 * - `errorClass(field)`: "input-error" if the field has any, else "".
 * - `unplaced`: the issues no field shows, for the form's banner.
 */
export function formIssues(issues, { area, index, fields }) {
  const all = issues ?? [];
  const inFields = (issue) => fields.some((f) => issue.field === f || issue.field?.startsWith(`${f}.`));

  function errorFor(field, exact = false) {
    const found = issuesFor(all, { area, index, field }).filter((issue) => !exact || issue.field === field);
    return found.length > 0 ? found.map((issue) => issue.message).join(" ") : undefined;
  }

  return {
    errorFor,
    errorClass: (field) => (errorFor(field) ? "input-error" : ""),
    unplaced: all.filter(
      (issue) => issue.area !== area || (index !== undefined && issue.index !== index) || !inFields(issue),
    ),
  };
}
