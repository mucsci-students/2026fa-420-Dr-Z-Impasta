// Description: Confirms a delete after showing what it affects (the impact preview).
//
// | impact part | Shown as
// | loading     | "Checking what this affects…" with a spinner
// | blocking    | "Can't delete X yet": the course sections that use it as their only room,
// |             | lab, or faculty member. Only a Close button; nothing can be deleted.
// | cascades    | "Delete X?": the references removed along with it, then Delete / Cancel
// | problems    | The library's issues, listed under either message

import Button from "../../../components/Button.jsx";
import ConfirmDialog from "../../../components/ConfirmDialog.jsx";
import Dialog from "../../../components/Dialog.jsx";
import ErrorMessage from "../../../components/ErrorMessage.jsx";
import IssueList from "../../../components/IssueList.jsx";
import Spinner from "../../../components/Spinner.jsx";

/** What a blocking reference makes the item, in words: "CMSC 161.01's only room". */
const ONLY_AS = { room: "only room", lab: "only lab", faculty: "only faculty member" };

/** Which list a cascading reference is removed from. */
const REMOVED_FROM = {
  room: "room options",
  lab: "lab options",
  faculty: "faculty candidates",
  conflicts: "conflicts",
  course_preferences: "course preferences",
  room_preferences: "room preferences",
  lab_preferences: "lab preferences",
};

/**
 * Shows a delete's impact preview and asks to confirm. `impact` is the reply from
 * api.config.deleteImpact(area, index), or null while it loads. `loadError` is a failure
 * to fetch it; `error` is a failed delete. Nothing is deleted until `onConfirm`.
 */
export default function DeleteDialog({ impact, loadError, busy, error, onConfirm, onCancel }) {
  if (loadError) {
    return (
      <Dialog
        open
        title="Couldn't check this delete"
        onClose={onCancel}
        actions={<Button onClick={onCancel} data-autofocus>Close</Button>}
      >
        <ErrorMessage error={loadError} title="Nothing was deleted." />
      </Dialog>
    );
  }

  if (!impact) {
    return (
      <Dialog open title="Delete" onClose={onCancel} actions={<Button onClick={onCancel} data-autofocus>Cancel</Button>}>
        <Spinner label="Checking what this affects…" />
      </Dialog>
    );
  }

  if (!impact.can_delete) {
    return (
      <Dialog
        open
        tone="danger"
        title={`Can't delete ${impact.label} yet`}
        onClose={onCancel}
        actions={<Button onClick={onCancel} data-autofocus>Close</Button>}
      >
        {impact.blocking.length > 0 && (
          <>
            <p>These sections depend on it. Edit them to use something else first:</p>
            <ul className="impact-list">
              {impact.blocking.map((ref) => (
                <li key={`${ref.area}-${ref.index}-${ref.field}`}>
                  <strong>{ref.label}</strong>: it's the {ONLY_AS[ref.field] ?? ref.field}
                </li>
              ))}
            </ul>
          </>
        )}
        <IssueList issues={impact.problems} />
        <p className="muted">Nothing was deleted.</p>
      </Dialog>
    );
  }

  return (
    <ConfirmDialog
      open
      destructive
      title={`Delete ${impact.label}?`}
      confirmLabel="Delete"
      busy={busy}
      onConfirm={onConfirm}
      onCancel={onCancel}
    >
      <ErrorMessage error={error} title="Not deleted." />
      {impact.cascades.length > 0 ? (
        <>
          <p>It will also be removed from:</p>
          <ul className="impact-list">
            {impact.cascades.map((ref) => (
              <li key={`${ref.area}-${ref.index}-${ref.field}`}>
                <strong>{ref.label}</strong>: {REMOVED_FROM[ref.field] ?? ref.field}
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p>Nothing else refers to it.</p>
      )}
      <IssueList issues={impact.problems} />
    </ConfirmDialog>
  );
}
