// Description: Generation limit (limit); optimizer flag chips. Default limit of 10?

import { useState } from "react";
import Card from "../../../components/Card.jsx";
import ErrorMessage from "../../../components/ErrorMessage.jsx";
import Field from "../../../components/Field.jsx";
import HelpTip from "../../../components/HelpTip.jsx";
import { issuesFor } from "../../../components/issues.js";
import { FLAG_NAMES } from "../labels.js";
import CardRow from "./CardRow.jsx";

const toNumber = (text) => (text === "" ? null : Number(text));
const toText = (number) => (number == null ? "" : String(number));

/**
 * Global settings, applied as they change: a flag on each click, the generation limit when
 * its box loses focus or Enter is pressed. `settings` is { limit, optimizer_flags } from the
 * document; an incomplete document may leave either out. `flags` is
 * api.config.options().optimizer_flags ([{ value, description }]), with a fallback until it
 * arrives. `onApply` gets only the field that changed, ready for api.config.updateSettings(values).
 */
export default function SettingsCard({ settings, flags, busy, error, onApply }) {
  const savedFlags = settings.optimizer_flags ?? [];
  const [limitText, setLimitText] = useState(toText(settings.limit));
  // The saved limit the box was last filled from; when it changes, refill the box
  const [shownLimit, setShownLimit] = useState(settings.limit);
  if (settings.limit !== shownLimit) {
    setShownLimit(settings.limit);
    setLimitText(toText(settings.limit));
  }
  // The flags as clicked, so a chip changes right away; reset to the saved ones when those change
  const [checkedFlags, setCheckedFlags] = useState(savedFlags);
  const [shownFlags, setShownFlags] = useState(JSON.stringify(savedFlags));
  if (JSON.stringify(savedFlags) !== shownFlags) {
    setShownFlags(JSON.stringify(savedFlags));
    setCheckedFlags(savedFlags);
  }

  const allFlags = flags?.length
    ? flags
    : Object.keys(FLAG_NAMES).map((value) => ({ value, description: undefined }));

  /** Turn a flag on or off, keeping the flags in the library's order. */
  function toggleFlag(value) {
    const on = new Set(checkedFlags);
    if (on.has(value)) on.delete(value);
    else on.add(value);
    const known = allFlags.map((flag) => flag.value);
    const unknown = checkedFlags.filter((v) => !known.includes(v));   // keep what we can't show
    const next = [...known.filter((v) => on.has(v)), ...unknown];
    setCheckedFlags(next);
    onApply?.({ optimizer_flags: next });
  }

  /** Send the limit if it differs from the saved one; the library checks it. */
  function applyLimit() {
    const limit = toNumber(limitText);
    if (limit !== (settings.limit ?? null)) onApply?.({ limit });
  }

  /** The library's message for one field. */
  function errorFor(field) {
    const found = issuesFor(error?.issues, { area: "settings", field });
    return found.length > 0 ? found.map((issue) => issue.message).join(" ") : undefined;
  }

  const flagsError = errorFor("optimizer_flags");

  // Problems with nowhere to appear on this card; the banner lists them instead
  const FIELDS = ["limit", "optimizer_flags"];
  const unplaced = (error?.issues ?? []).filter((issue) =>
    issue.area !== "settings" ||
    !FIELDS.some((f) => issue.field === f || issue.field?.startsWith(`${f}.`)),
  );

  return (
    <CardRow title="Global Settings">
      <Card className="settings-card">
        <ErrorMessage
          error={error && { message: error.issues?.length ? "The change was not applied." : error.message, issues: unplaced }}
          title="Not saved."
        />
        <Field
          label="Generation limit"
          inline
          required
          help="The most schedules to generate in one run."
          error={errorFor("limit")}
        >
          <input type="number" min={1} className="settings-card__limit" value={limitText} disabled={busy}
            onChange={(e) => setLimitText(e.target.value)}
            onBlur={applyLimit}
            onKeyDown={(e) => { if (e.key === "Enter") applyLimit(); }} />
        </Field>

        <fieldset className="flag-list">
          <legend>Optimizer flags</legend>
          {allFlags.map(({ value, description }) => (
            <span key={value} className="flag-chip">
              <label>
                <input type="checkbox" checked={checkedFlags.includes(value)} disabled={busy}
                  onChange={() => toggleFlag(value)} />
                {FLAG_NAMES[value] ?? value}
              </label>
              {description && <HelpTip text={description} />}
            </span>
          ))}
          {flagsError && (
            <p className="field__error">
              <span aria-hidden="true">⚠ </span>
              {flagsError}
            </p>
          )}
        </fieldset>
      </Card>
    </CardRow>
  );
}
