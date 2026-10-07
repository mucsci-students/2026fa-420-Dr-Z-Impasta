// Description:
// | Field                | Control               | Notes
// | times[DAY]           | list, add/remove rows | Each weekday needs at least one block; the
// |                      |                       | library reports an empty one. Saving sends
// |                      |                       | the whole times object, not just this day
// | times[DAY][].start   | time, required        |
// | times[DAY][].end     | time, required        |
// | times[DAY][].spacing | number (minutes)      | Minutes between slots

import { useState } from "react";
import Button from "../../../components/Button.jsx";
import ConfirmDialog from "../../../components/ConfirmDialog.jsx";
import Dialog from "../../../components/Dialog.jsx";
import ErrorMessage from "../../../components/ErrorMessage.jsx";
import UnsavedChangesPrompt from "../../../components/UnsavedChangesPrompt.jsx";
import { issuesFor } from "../../../components/issues.js";
import { DAY_NAMES } from "../labels.js";
import { hourAfter } from "../times.js";

/** A day's first block, when it has none. */
const FIRST_BLOCK = { start: "08:00", end: "17:00", spacing: 60 };

const toNumber = (text) => (text === "" ? null : Number(text));

/** A new block: the working day if there are none, else an hour after the last block, same spacing. */
function nextBlock(blocks) {
  const last = blocks.at(-1);
  if (!last?.end) return { ...FIRST_BLOCK };
  return { start: last.end, end: hourAfter(last.end), spacing: last.spacing ?? FIRST_BLOCK.spacing };
}

// Row keys for blocks, so removing a row doesn't hand its state to the next one
let nextBlockKey = 0;
const newBlockKeys = (count) => Array.from({ length: count }, () => nextBlockKey++);

/**
 * Edit one weekday's time blocks. `times` is the whole time_slot_config.times object;
 * Save hands back the whole object with this day's blocks swapped in, ready for
 * api.config.updateTimeSlots({ times }).
 */
export default function DayBlocksDialog({ day, times, busy, error, onSave, onCancel, localError }) {
  const name = DAY_NAMES[day] ?? day;
  const original = times[day] ?? [];
  const [blocks, setBlocks] = useState(original);
  const isDirty = JSON.stringify(blocks) !== JSON.stringify(original);
  const [confirmingDiscard, setConfirmingDiscard] = useState(false);

  // One key per row of blocks, in the same order
  const [blockKeys, setBlockKeys] = useState(() => newBlockKeys(original.length));
  // The row keys when Save was last pressed; the server's `times.DAY.N` errors refer to these positions
  const [savedKeys, setSavedKeys] = useState(blockKeys);

  /** Cancel, Escape, or ×: ask first if there are unsaved edits. */
  function requestClose() {
    if (isDirty) setConfirmingDiscard(true);
    else onCancel?.();
  }

  function save() {
    setSavedKeys(blockKeys);
    onSave?.({ ...times, [day]: blocks});
  }

  /** Change one field of block number i. */
  function setBlock(i, field, value) {
    setBlocks(blocks.map((block, j) => (j === i ? { ...block, [field]: value } : block)));
  }

  function addBlock() {
    const [key] = newBlockKeys(1);
    setBlocks([...blocks, nextBlock(blocks)]);
    setBlockKeys((keys) => [...keys, key]);
  }

  function removeBlock(i) {
    setBlocks(blocks.filter((_, j) => j !== i));
    setBlockKeys((keys) => keys.filter((_, j) => j !== i));
  }

  /** The library's message for a field of this day. `exact` leaves out the issues for its sub-fields. */
  function errorFor(field, exact = false) {
    const found = issuesFor(error?.issues, { area: "time_slots", field }).filter(
      (issue) => !exact || issue.field === field,
    );
    return found.length > 0 ? found.map((issue) => issue.message).join(" ") : undefined;
  }

	/** A function to assign the input field the 'input-error' class if it contains invalid data */
	function classNameFunc(field) {
		if(localError.some((err) => err.field.split(".")[3] === field)) {
			return "input-error";
		} else {
			return "";
		}
	}


  /** The library's message for the block row with this key, from where it was at the last Save. */
  function blockError(key) {
    const position = savedKeys.indexOf(key);
    return position === -1 ? undefined : errorFor(`times.${day}.${position}`);
  }

  const dayError = errorFor(`times.${day}`, true);

  // The prompts are siblings of the Dialog, not children; see ResourceDialog.
  return (
    <>
      <Dialog
        open
        width="520px"
        title={`${name} time blocks`}
        onClose={requestClose}
        actions={
          <>
            <Button onClick={requestClose} disabled={busy}>Cancel</Button>
            <Button variant="primary" busy={busy} onClick={save}>Save</Button>
          </>
        }
      >
        <ErrorMessage error={error} title="Not saved." />

        <fieldset className="blocks-editor">
          <legend>Blocks on {name}</legend>
          <div className="blocks-editor__head" aria-hidden="true">
            <span>Start</span><span>End</span><span>Spacing (min)</span><span />
          </div>
          {blocks.length === 0 && <p className="muted">No blocks. {name} needs at least one.</p>}
          {blocks.map((block, i) => {
            const rowError = blockError(blockKeys[i]);
            return (
              <div key={blockKeys[i]} className="blocks-editor__row">
                <input className={classNameFunc("start")} type="time" aria-label={`Block ${i + 1} start`} value={block.start ?? ""}
                  onChange={(e) => setBlock(i, "start", e.target.value)} data-autofocus={i === 0 || undefined} />
                <input className={classNameFunc("end")} type="time" aria-label={`Block ${i + 1} end`} value={block.end ?? ""}
                  onChange={(e) => setBlock(i, "end", e.target.value)} />
                <input className={classNameFunc("spacing")} type="number" min={1} aria-label={`Block ${i + 1} spacing in minutes`} value={block.spacing ?? ""}
                  onChange={(e) => setBlock(i, "spacing", toNumber(e.target.value))} />
                <button type="button" className="blocks-editor__remove" aria-label={`Remove block ${i + 1}`}
                  onClick={() => removeBlock(i)}>
                  ×
                </button>
                {rowError && (
                  <p className="field__error blocks-editor__error">
                    <span aria-hidden="true">⚠ </span>
                    {rowError}
                  </p>
                )}
              </div>
            );
          })}
          <Button size="sm" variant="ghost" onClick={addBlock}>
            + Add block
          </Button>
          {dayError && (
            <p className="field__error">
              <span aria-hidden="true">⚠ </span>
              {dayError}
            </p>
          )}
        </fieldset>
      </Dialog>
      <UnsavedChangesPrompt when={isDirty} />
      <ConfirmDialog
        open={confirmingDiscard}
        title="Discard changes?"
        destructive
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        onConfirm={onCancel}
        onCancel={() => setConfirmingDiscard(false)}
      >
        <p>Your changes to {name}'s time blocks haven't been saved.</p>
      </ConfirmDialog>
    </>
  );
}
