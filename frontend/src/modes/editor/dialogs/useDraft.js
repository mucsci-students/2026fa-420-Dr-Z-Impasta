import { useState } from "react";

/**
 * An edit dialog's draft: a copy of `original` that changes locally until the dialog saves
 * it. `set(field, value)` changes one field of an object draft; `isDirty` is true while the
 * draft differs from `original`. Pass `isDirty` to EditDialog so closing asks first.
 */
export function useDraft(original) {
  const [draft, setDraft] = useState(original);
  const isDirty = JSON.stringify(draft) !== JSON.stringify(original);

  function set(field, value) {
    setDraft((d) => ({ ...d, [field]: value }));
  }

  return { draft, setDraft, set, isDirty };
}
