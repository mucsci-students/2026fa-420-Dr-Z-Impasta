/**
 * Schedule Generator (mode 02).
 *
 * Runs the scheduler on the last validated configuration.
 * Run-specific settings are sent as overrides and never change the saved configuration.
 */

import { useEffect, useState } from "react";
import { Link } from "react-router";
import Badge from "../../components/Badge.jsx";
import Button from "../../components/Button.jsx";
import Card from "../../components/Card.jsx";
import EmptyState from "../../components/EmptyState.jsx";
import ErrorMessage from "../../components/ErrorMessage.jsx";
import Field from "../../components/Field.jsx";
import PageHeader from "../../components/PageHeader.jsx";
import { Rotelle } from "../../components/PastaMarks.jsx";
import Spinner from "../../components/Spinner.jsx";
import { plural } from "../../format.js";
import { api } from "../../api/client.js";
import { useAppState } from "../../state/appStateContext.js";
import { useAction } from "../../state/useAction.js";

const FLAG_NAMES = {
  faculty_course: "Faculty course preferences",
  faculty_room: "Faculty room preferences",
  faculty_lab: "Faculty lab preferences",
  same_room: "Same room",
  same_lab: "Same lab",
  pack_rooms: "Pack rooms",
  pack_labs: "Pack labs",
};

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
  const { state, loading, refresh } = useAppState();

  const [options, setOptions] = useState(null);
  const [optionsError, setOptionsError] = useState(null);
  const [limit, setLimit] = useState("");
  const [optimizerFlags, setOptimizerFlags] = useState([]);

  const startGeneration = useAction(async () => {
    const parsedLimit = limit === "" ? undefined : Number(limit);

    return api.generation.start({
      limit: parsedLimit,
      optimizerFlags,
    });
  });

  const cancelGeneration = useAction(() => api.generation.cancel());

  useEffect(() => {
    let cancelled = false;

    async function loadOptions() {
      try {
        const result = await api.config.options();

        if (cancelled) return;

        setOptions(result);
      } catch (error) {
        if (!cancelled) setOptionsError(error);
      }
    }

    if (state?.config?.status === "valid") {
      loadOptions();
    }

    return () => {
      cancelled = true;
    };
  }, [state?.config?.status]);

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
          mark={<Rotelle size={40} />}
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
  const schedules = state.schedules;
  const running = generation.running;

  const maxLimit = options?.generation?.max_schedules ?? null;
  const optimizerOptions = options?.optimizer_flags ?? [];

  function toggleOptimizer(flag) {
    setOptimizerFlags((current) =>
      current.includes(flag)
        ? current.filter((item) => item !== flag)
        : [...current, flag],
    );
  }

  async function handleGenerate() {
    const result = await startGeneration.run();

    if (result.ok) {
      await refresh();
    }
  }

  async function handleCancel() {
    const result = await cancelGeneration.run();

    if (result.ok) {
      await refresh();
    }
  }

  return (
    <>
      <PageHeader title="Generate schedules" subtitle={SUBTITLE} />

      <div className="columns">
        <div className="columns__main">
          <Card title="Generation settings">
            <div className="stack">
              <Field
                label="Number of schedules"
                help={
                  maxLimit === null
                    ? "The maximum number of schedules to generate."
                    : `Choose how many schedules to generate, up to ${maxLimit}.`
                }
              >
                <input
                  type="number"
                  min="1"
                  max={maxLimit ?? undefined}
                  value={limit}
                  disabled={running || startGeneration.busy}
                  onChange={(event) => setLimit(event.target.value)}
                  placeholder="Use configured limit"
                />
              </Field>

              {optimizerOptions.length > 0 && (
                <fieldset className="flag-list">
                  <legend>Optimizer options</legend>

                  {optimizerOptions.map(({ value, description }) => (
                    <span key={value} className="flag-chip">
                      <label>
                        <input
                          type="checkbox"
                          checked={optimizerFlags.includes(value)}
                          disabled={running || startGeneration.busy}
                          onChange={() => toggleOptimizer(value)}
                        />
                        {FLAG_NAMES[value] ?? value}
                      </label>

                      {description && (
                        <span className="muted">{description}</span>
                      )}
                    </span>
                  ))}
                </fieldset>
              )}

              <ErrorMessage
                error={optionsError}
                title="Couldn't load generation options."
                onDismiss={() => setOptionsError(null)}
              />

              <ErrorMessage
                error={startGeneration.error}
                title="Couldn't start generation."
                onDismiss={startGeneration.clearError}
              />

              <ErrorMessage
                error={cancelGeneration.error}
                title="Couldn't cancel generation."
                onDismiss={cancelGeneration.clearError}
              />

              <div className="card__actions">
                {running ? (
                  <Button
                    variant="danger"
                    busy={cancelGeneration.busy}
                    onClick={handleCancel}
                  >
                    Cancel generation
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    busy={startGeneration.busy}
                    onClick={handleGenerate}
                  >
                    Generate schedules
                  </Button>
                )}
              </div>
            </div>
          </Card>

          {generation.state !== "idle" && (
            <Card
              title="Last run"
              actions={
                <Badge tone={OUTCOME_TONES[generation.state]}>
                  {generation.state.replace("_", " ")}
                </Badge>
              }
            >
              <p>{generation.message}</p>

              {generation.running && (
                <div>
                  <p>{plural(generation.found, "schedule")} found.</p>
                  <Spinner label="Generating schedules" />
                </div>
              )}

              {generation.state === "succeeded" && schedules.count > 0 && (
                <p>
                  <Link className="btn btn--primary" to="/viewer">
                    View schedules
                  </Link>
                </p>
              )}

              {generation.detail && (
                <p className="muted">{generation.detail}</p>
              )}
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
            Only applied, validated edits are used. Open drafts in the editor
            are ignored.
          </p>

          {config.dirty && (
            <p className="muted">
              {plural(config.changes.length, "change")} not saved to a file
              yet.
            </p>
          )}
        </Card>
      </div>
    </>
  );
}
