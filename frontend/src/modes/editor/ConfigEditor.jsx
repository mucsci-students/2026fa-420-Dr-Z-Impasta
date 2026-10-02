/**
 * Configuration Editor (mode 01).
 *
 * The foundation provides the page frame and its empty and summary states. The
 * Configuration Editor feature adds: New / Load JSON… / Save JSON… / Validate, the item
 * cards and their edit dialogs, deletes with the impact preview, time slots, and global
 * settings. Start from docs/gui.md; the calls are in src/api/client.js (`api.config`).
 */
import EmptyState from "../../components/EmptyState.jsx";
import IssueList from "../../components/IssueList.jsx";
import PageHeader from "../../components/PageHeader.jsx";
import { Penne } from "../../components/PastaMarks.jsx";
import Spinner from "../../components/Spinner.jsx";
import { clockTime, configStatus, describeCounts, plural } from "../../format.js";
import { useAppState } from "../../state/appStateContext.js";
import { useEffect, useState, useRef } from "react";
import { api } from "../../api/client.js";
import Button from "../../components/Button.jsx";
import Banner from "../../components/Banner.jsx";
import CardRow from "./cards/CardRow.jsx";
import ResourceCard from "./cards/ResourceCard.jsx";
import CourseCard from "./cards/CourseCard.jsx";

import { loadConfiguration } from "../../components/APICommunication";

export default function ConfigEditor() {
  const { state, loading } = useAppState();
  const config = state?.config;
  const [doc, setDoc] = useState(null);
	const[loadingFile, setLoadingFile] = useState(false);
  const revision = config?.revision;
  const hasConfig = Boolean(config) && config.status !== "none";
  const fileInputRef = useRef(null)

  useEffect(() => {
    if (!hasConfig) return;
    api.config.get().then((reply) => {
      setDoc({ document: reply.document, sections: reply.sections });
    });
  }, [hasConfig,revision]);

  if (loading || loadingFile) {
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
        <EmptyState
          title="No configuration loaded"
          mark={<Penne size={40} />}
          actions={
            <>
              <Button variant="primary">New</Button>

		  <Button onClick={() => { fileInputRef.current.click(); }}>Load JSON...</Button>
		  <input 
		  ref={fileInputRef}
		  type="file"
		  style={{display: "none"}}
		  onChange={async (event) => {
			  setLoadingFile(true);
			  const file = event.target.files[0];
			  if(!file) return;
			  try {
				  const res = await loadConfiguration(file);
				  
				  if(!res.ok) {
					  throw new Error("Invalid configuration file");
				  }
				  else {
					  return res.json();
				  }
			  } catch(err) {
				  return err;
			  } finally {
				  await new Promise(resolve => setTimeout(resolve, 2000));
				  config.status = "valid"; 
				  setLoadingFile(false);
			  }
		  }}
		  />
            </>
          }
        >
          Create an empty configuration to add rooms, labs, courses, and faculty, or load an
          existing JSON file. Files are validated before anything is replaced. The Schedule
          Generator and Viewer need a valid configuration or loaded schedules.
        </EmptyState>
      </>
    );
  }

  const status = configStatus(config);
  const bannerTone = status.tone === "neutral" ? "info" : status.tone;
  const items = doc?.document.config;                     // rooms, labs, courses, faculty
  const patterns = doc?.document.time_slot_config.classes; // class patterns
  const enabled = patterns?.filter((p) => !p.disabled).length;
  return (
    <div className="editor">
      <PageHeader
        title="Configuration"
        subtitle={
          <>
            Editing <span className="mono">{config.name ?? "an unsaved configuration"}</span>
            {config.validated_at && <> · last validated {clockTime(config.validated_at)}</>}
          </>
        }
        actions={
          <>
            <Button variant="ghost">Raw JSON</Button>
            <Button>New</Button>

		<Button onClick={() => fileInputRef.current.click()}>Load JSON...</Button>
		<input
		ref={fileInputRef}
		type="file"
		style={{display: "none"}}
		onChange={async (event) => {
			setLoadingFile(true);
			const file = event.target.files[0];
			if (!file) return;
			try {
				const res = await loadConfiguration(file);
				if(!res.ok) {
				//	config.status = "none";
					throw new Error("Invalid configuration file");
					return res;
				} else {
				//	config.status = "valid";
					return res.json();
				}
			} catch(err) {
				return err;
			} finally {
				await new Promise(resolve => setTimeout(resolve, 2000));
				setLoadingFile(false);
			  }
		}}
		/>

            <Button>Save JSON...</Button>
            <Button variant="primary">Validate</Button>
          </>
        }
      />
      <Banner tone={bannerTone} title={status.label}>
      {describeCounts(config.counts)}.
      {config.status === "incomplete" && <IssueList issues={config.issues} />}
      </Banner>
      {!doc ? (
        <Spinner label="Loading the configuration" />
      ) : (
        <>
          <CardRow title="Faculty" meta={items.faculty.length} addLabel="Add faculty">
            {items.faculty.map((f, i) => (
              <div key={i}>{f.name}</div>
            ))}
          </CardRow>
          <CardRow title="Courses" meta={plural(items.courses.length, "section")} addLabel="Add course">
            {items.courses.map((c, i) => (
              <CourseCard
                key={i}
                course={c}
                label={doc.sections[i]}
              />
            ))}
          </CardRow>
          <div className="editor-pair">
          <CardRow title="Rooms" meta={items.rooms.length} addLabel="Add room">
            {items.rooms.map((r, i) => (
              <ResourceCard
                key={i}
                resource={r}
                usedBy={items.courses.filter((c) => c.room.includes(r.name)).length}
              />
            ))}
          </CardRow>
          <CardRow title="Labs" meta={items.labs.length} addLabel="Add lab">
            {items.labs.map((l, i) => (
              <ResourceCard
                key={i}
                resource={l}  
                usedBy={items.courses.filter((c) => c.lab.includes(l.name)).length}
              />
            ))}
          </CardRow>
          </div>
          <CardRow title="Class Patterns" meta={`${enabled} of ${patterns.length} enabled`} addLabel="Add pattern">
            {patterns.map((p, i) => (
              <div key={i}>{`${p.credits} credits`}</div>
            ))}
          </CardRow>
          {/* Later: TimeSlotsCard and SettingsCard (edit-only, not part of this pass) */}
        </>
      )}
    </div>
  );
}
