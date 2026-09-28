import { describeIssueLocation } from "./issues.js";

/** The located problems from an API error or a validation report. */
export default function IssueList({ issues, labels, limit = 20 }) {
  if (!issues?.length) return null;
  const shown = issues.slice(0, limit);
  return (
    <ul className="issues">
      {shown.map((issue, position) => {
        const where = describeIssueLocation(issue, labels);
        return (
          <li key={`${issue.path}-${position}`} className="issues__item">
            {where && <span className="issues__where">{where}</span>}
            <span>{issue.message}</span>
          </li>
        );
      })}
      {issues.length > limit && (
        <li className="issues__more">and {issues.length - limit} more</li>
      )}
    </ul>
  );
}
