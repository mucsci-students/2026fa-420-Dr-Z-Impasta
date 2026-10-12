/** Small, shared wording helpers, so every mode says things the same way. */

export function plural(count, singular, pluralForm = `${singular}s`) {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

/** "16:41" from an ISO timestamp, or "" when missing. */
export function clockTime(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}

/**
 * The configuration's status for the header pill: `{ tone, label }`.
 * Reads the `config` part of GET /api/state.
 */
export function configStatus(config) {
  if (!config) return { tone: "neutral", label: "Connecting…" };
  switch (config.status) {
    case "none":
      return { tone: "neutral", label: "No configuration loaded" };
    case "incomplete":
      return { tone: "warning", label: "Incomplete" };
    default:
      if (config.dirty && config.changes.length) {
        return { tone: "warning", label: `Unsaved changes (${config.changes.length})` };
      }
      return config.name
        ? { tone: "success", label: "Valid · saved" }
        : { tone: "warning", label: "Valid · not saved" };
  }
}

/** "17 course sections, 9 faculty, 3 rooms, 2 labs, 9 of 16 class patterns enabled". */
export function describeCounts(counts) {
  if (!counts) return "";
  return [
    plural(counts.sections, "course section"),
    `${counts.faculty} faculty`,
    plural(counts.rooms, "room"),
    plural(counts.labs, "lab"),
    `${counts.enabled_patterns} of ${plural(counts.patterns, "class pattern")} enabled`,
  ].join(", ");
}
