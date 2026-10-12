import { isRouteErrorResponse, Link, useRouteError } from "react-router";
import Button from "../components/Button.jsx";

/**
 * Shown if a page crashes while rendering. The configuration and schedules live on the
 * server, so reloading the page loses nothing that was applied.
 */
export default function ErrorPage() {
  const error = useRouteError();
  const detail = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : error instanceof Error
      ? error.message
      : String(error);
  return (
    <main className="page page--narrow" id="main">
      <div className="empty">
        <h1 className="empty__title">Something went wrong on this page</h1>
        <div className="empty__text">
          <p>
            The page couldn't be displayed. Your configuration and schedules are kept by the server,
            so reloading loses nothing you already applied.
          </p>
          <details className="details">
            <summary>Technical details</summary>
            <pre>{detail}</pre>
          </details>
        </div>
        <div className="empty__actions">
          <Button variant="primary" onClick={() => window.location.reload()}>
            Reload the page
          </Button>
          <Link className="btn btn--secondary" to="/editor" reloadDocument>
            Go to the Configuration Editor
          </Link>
        </div>
      </div>
    </main>
  );
}
