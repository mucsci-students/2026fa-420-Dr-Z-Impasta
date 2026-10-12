import Banner from "./Banner.jsx";
import IssueList from "./IssueList.jsx";

/**
 * Show a failed action: the server's message, its located issues, and for unexpected
 * errors the reference to quote when reporting it. Works with ApiError and plain Error.
 */
export default function ErrorMessage({ error, title = "That didn't work.", labels, onDismiss }) {
  if (!error) return null;
  return (
    <Banner tone="danger" title={title} onDismiss={onDismiss}>
      {error.message}
      <IssueList issues={error.issues} labels={labels} />
    </Banner>
  );
}
