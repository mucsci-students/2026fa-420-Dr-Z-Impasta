import { Link } from "react-router";
import EmptyState from "../components/EmptyState.jsx";
import { Ravioli } from "../components/PastaMarks.jsx";

export default function NotFound() {
  return (
    <EmptyState
      title="There's no page here"
      mark={<Ravioli size={40} />}
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
