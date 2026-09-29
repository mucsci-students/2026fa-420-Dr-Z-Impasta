/**
 * Configuration Editor (mode 01).
 *
 * The foundation provides the page frame and its empty and summary states. The
 * Configuration Editor feature adds: New / Load JSON… / Save JSON… / Validate, the item
 * cards and their edit dialogs, deletes with the impact preview, time slots, and global
 * settings. Start from docs/gui.md; the calls are in src/api/client.js (`api.config`).
 */
import Card from "../../components/Card.jsx";
import EmptyState from "../../components/EmptyState.jsx";
import IssueList from "../../components/IssueList.jsx";
import PageHeader from "../../components/PageHeader.jsx";
import Spinner from "../../components/Spinner.jsx";
import StatusPill from "../../components/StatusPill.jsx";
import { clockTime, configStatus, describeCounts } from "../../format.js";
import { useAppState } from "../../state/appStateContext.js";

export default function ConfigEditor() {
  const { state, loading } = useAppState();
  const config = state?.config;

  if (loading) {
    return (
      <>
        <PageHeader title="Configuration" />
        <Spinner label="Loading the configuration" />
      </>
    );
  }

  if (!config || config.status === "none") {
    return (
      <>
        <PageHeader title="Configuration" subtitle="Start a new configuration or load one from a JSON file." />
        <EmptyState title="No configuration loaded">
          Create an empty configuration to add rooms, labs, courses, and faculty, or load an
          existing JSON file. Files are validated before anything is replaced. The Schedule
          Generator and Viewer need a valid configuration or loaded schedules.
        </EmptyState>
      </>
    );
  }

  const status = configStatus(config);
  return (
    <>
      <PageHeader
        title="Configuration"
        subtitle={
          <>
            Editing <span className="mono">{config.name ?? "an unsaved configuration"}</span>
            {config.validated_at && <> · last validated {clockTime(config.validated_at)}</>}
          </>
        }
      />
      <Card title="Summary" actions={<StatusPill tone={status.tone}>{status.label}</StatusPill>}>
        <p>{describeCounts(config.counts)}.</p>
        {config.status === "incomplete" && (
          <>
            <p>This new configuration isn't complete yet:</p>
            <IssueList issues={config.issues} />
          </>
        )}
      </Card>
    </>
  );
}
