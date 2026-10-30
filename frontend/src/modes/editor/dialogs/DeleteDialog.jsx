/**
 * Opens when Delete is pressed in an edit dialog. Shows one of: a spinner while the preview loads,
 * "Couldn't check this delete", "Delete X anyway?" (a warning: sections would lose their only
 * room, lab, or faculty member, or the configuration would have problems to fix; the user can
 * still delete), "Can't delete X" (the rare delete the server can't keep at all), or "Delete X?"
 * with everything else the delete removes.
 */

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
 * to fetch it; `error` is a failed delete. Nothing is deleted until `onConfirm`; when
 * `impact.can_delete` is false the caller sends the delete with force.
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

  if (!impact.can_delete && !impact.can_force) {
    return (
      <Dialog
        open
        tone="danger"
        title={`Can't delete ${impact.label}`}
        onClose={onCancel}
        actions={<Button onClick={onCancel} data-autofocus>Close</Button>}
      >
        <p>Deleting it would leave something the configuration can't keep. Fix these first:</p>
        <IssueList issues={impact.problems} />
        <p className="muted">Nothing was deleted.</p>
      </Dialog>
    );
  }

  const warning = !impact.can_delete;   // it can still be deleted, but it breaks something
  return (
    <ConfirmDialog
      open
      destructive
      title={warning ? `Delete ${impact.label} anyway?` : `Delete ${impact.label}?`}
      confirmLabel={warning ? "Delete anyway" : "Delete"}
      busy={busy}
      onConfirm={onConfirm}
      onCancel={onCancel}
    >
      <ErrorMessage error={error} title="Not deleted." />
      {impact.blocking.length > 0 && (
        <>
          <p>These sections will be left without it:</p>
          <ul className="impact-list">
            {impact.blocking.map((ref) => (
              <li key={`${ref.area}-${ref.index}-${ref.field}`}>
                <strong>{ref.label}</strong>: it's the {ONLY_AS[ref.field] ?? ref.field}
              </li>
            ))}
          </ul>
        </>
      )}
      {impact.cascades.length > 0 && (
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
      )}
      {impact.blocking.length === 0 && impact.cascades.length === 0 && <p>Nothing else refers to it.</p>}
      {impact.problems.length > 0 && (
        <>
          <p>The configuration will have problems to fix:</p>
          <IssueList issues={impact.problems} />
          <p className="muted">You can't save it or generate schedules until they're fixed.</p>
        </>
      )}
    </ConfirmDialog>
  );
}
