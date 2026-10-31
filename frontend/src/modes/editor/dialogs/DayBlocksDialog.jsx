/**
 * The dialog for one weekday's time blocks, opened from a day's tile on TimeSlotsCard. It's an
 * edit dialog like CourseDialog. Each block is a start, an end, and the spacing in minutes between
 * slots. Save sends the whole `times` object, with every day, not just this one.
 */

import { useState } from "react";
import Button from "../../../components/Button.jsx";
import { formIssues } from "../../../components/issues.js";
import { DAY_NAMES } from "../labels.js";
import { hourAfter } from "../times.js";
import EditDialog from "./EditDialog.jsx";
import { useDraft } from "./useDraft.js";

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
export default function DayBlocksDialog({ day, times, busy, error, onSave, onCancel }) {
  const name = DAY_NAMES[day] ?? day;
  const original = times[day] ?? [];
  const { draft: blocks, setDraft: setBlocks, isDirty } = useDraft(original);

  // One key per row of blocks, in the same order
  const [blockKeys, setBlockKeys] = useState(() => newBlockKeys(original.length));
  // The row keys when Save was last pressed; the server's `times.DAY.N` errors refer to these positions
  const [savedKeys, setSavedKeys] = useState(blockKeys);

  function save() {
    setSavedKeys(blockKeys);
    onSave?.({ ...times, [day]: blocks });
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

  const { errorFor, unplaced } = formIssues(error?.issues, {
    area: "time_slots",
    fields: [`times.${day}`],
  });

  /**
   * The field the server's errors use for the block row with this key ("times.MON.2"), from
   * where the row was at the last Save, or null if it was added since.
   */
  function blockField(key) {
    const position = savedKeys.indexOf(key);
    return position === -1 ? null : `times.${day}.${position}`;
  }

  const dayError = errorFor(`times.${day}`, true);

  /** "input-error" if any block, on any day, has an issue with this `part` (start, end, spacing). */
  function partClass(part) {
    return (error?.issues ?? []).some((issue) => issue.field?.split(".")[3] === part) ? "input-error" : "";
  }

  return (
    <EditDialog
      width="520px"
      title={`${name} time blocks`}
      what={`${name}'s time blocks`}
      isDirty={isDirty}
      error={error}
      unplaced={unplaced}
      busy={busy}
      onSave={save}
      onCancel={onCancel}
    >
      <fieldset className="blocks-editor">
        <legend>Blocks on {name}</legend>
        <div className="blocks-editor__head" aria-hidden="true">
          <span>Start</span><span>End</span><span>Spacing (min)</span><span />
        </div>
        {blocks.length === 0 && <p className="muted">No blocks. {name} needs at least one.</p>}
        {blocks.map((block, i) => {
          const rowField = blockField(blockKeys[i]);
          const rowError = rowField && errorFor(rowField);
          return (
            <div key={blockKeys[i]} className="blocks-editor__row">
              <input className={partClass("start")} type="time" aria-label={`Block ${i + 1} start`} value={block.start ?? ""}
                onChange={(e) => setBlock(i, "start", e.target.value)} data-autofocus={i === 0 || undefined} />
              <input className={partClass("end")} type="time" aria-label={`Block ${i + 1} end`} value={block.end ?? ""}
                onChange={(e) => setBlock(i, "end", e.target.value)} />
              <input className={partClass("spacing")} type="number" min={1} aria-label={`Block ${i + 1} spacing in minutes`} value={block.spacing ?? ""}
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
    </EditDialog>
  );
}
