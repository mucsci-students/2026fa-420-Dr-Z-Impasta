/**
 * The "Edit" button at the bottom of every card in the Configuration Editor's rows. It's the
 * only way to open a card's dialog: the card itself isn't clickable, so its text can be
 * selected and a stray click never opens anything. `label` names the card for screen
 * readers: "Edit Hardy".
 */

import Button from "../../../components/Button.jsx";

export default function EditButton({ label, onEdit }) {
  return (
    <div className="item-card__actions">
      <Button aria-label={label ? `Edit ${label}` : "Edit"} onClick={onEdit}>
        Edit
      </Button>
    </div>
  );
}
