/**
 * Schedule Generator (mode 02).
 *
 * The foundation provides the page frame, the "needs a valid configuration" state, and
 * the configuration-in-use summary. The Schedule Generator feature adds the run settings
 * (limit and optimizer overrides), the Generate button, progress and cancel, and the
 * result card. Start from docs/gui.md; the calls are `api.generation` in src/api/client.js,
 * and `state.generation` (polled every 0.6 s while running) has the live status.
 */
import { Link } from "react-router";
import Badge from "../../components/Badge.jsx";
import Card from "../../components/Card.jsx";
import EmptyState from "../../components/EmptyState.jsx";
import PageHeader from "../../components/PageHeader.jsx";
import Spinner from "../../components/Spinner.jsx";
import { plural } from "../../format.js";
import { useAppState } from "../../state/appStateContext.js";

const SUBTITLE =
  "Runs the scheduler on the last validated configuration. Overrides apply to this run only and never change the saved file.";

const OUTCOME_TONES = {
  running: "info",
  succeeded: "success",
  infeasible: "warning",
  solver_error: "warning",
  failed: "danger",
  cancelled: "neutral",
};

export default function ScheduleGenerator() {
  const { state, loading } = useAppState();

  if (loading) {
    return (
      <>
        <PageHeader title="Generate schedules" subtitle={SUBTITLE} />
        <Spinner label="Loading" />
      </>
    );
  }

  const config = state?.config;
  if (config?.status !== "valid") {
    return (
      <>
        <PageHeader title="Generate schedules" subtitle={SUBTITLE} />
        <EmptyState
          title="A valid configuration is needed"
          actions={
            <Link className="btn btn--primary" to="/editor">
              Open the Configuration Editor
            </Link>
          }
        >
          {config?.status === "incomplete"
            ? "The configuration in the editor isn't complete yet. Finish it, then come back to generate schedules."
            : "Create or load a configuration in the Configuration Editor, then come back to generate schedules."}
        </EmptyState>
      </>
    );
  }

  const generation = state.generation;
  return (
    <>
      <PageHeader title="Generate schedules" subtitle={SUBTITLE} />
      <div className="columns">
        <div className="columns__main">
          {generation.state !== "idle" && (
            <Card
              title="Last run"
              actions={<Badge tone={OUTCOME_TONES[generation.state]}>{generation.state.replace("_", " ")}</Badge>}
            >
              <p>{generation.message}</p>
            </Card>
          )}
        </div>
        <Card className="columns__side" title="Configuration in use">
          <p className="mono">{config.name ?? "Unsaved configuration"}</p>
          <dl className="facts">
            <dt>Course sections</dt>
            <dd>{config.counts.sections}</dd>
            <dt>Faculty</dt>
            <dd>{config.counts.faculty}</dd>
            <dt>Rooms</dt>
            <dd>{config.counts.rooms}</dd>
            <dt>Labs</dt>
            <dd>{config.counts.labs}</dd>
            <dt>Class patterns</dt>
            <dd>
              {config.counts.enabled_patterns} / {config.counts.patterns}
            </dd>
          </dl>
          <p className="muted">
            Only applied, validated edits are used. Open drafts in the editor are ignored.
          </p>
          {config.dirty && <p className="muted">{plural(config.changes.length, "change")} not saved to a file yet.</p>}
        </Card>
      </div>
    </>
  );
}
