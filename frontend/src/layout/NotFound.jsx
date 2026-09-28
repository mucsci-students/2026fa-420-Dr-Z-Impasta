import { Link } from "react-router";
import EmptyState from "../components/EmptyState.jsx";

export default function NotFound() {
  return (
    <EmptyState
      title="There's no page here"
      actions={
        <Link className="btn btn--primary" to="/editor">
          Go to the Configuration Editor
        </Link>
      }
    >
      Use the tabs at the top to switch between the Configuration Editor, Schedule Generator, and
      Schedule Viewer.
    </EmptyState>
  );
}
