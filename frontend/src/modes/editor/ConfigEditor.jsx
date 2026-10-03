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
import FacultyCard from "./cards/FacultyCard.jsx";
import PatternCard from "./cards/PatternCard.jsx";
import ResourceDialog from "./dialogs/ResourceDialog.jsx";
import CourseDialog from "./dialogs/CourseDialog.jsx";
import PatternDialog from "./dialogs/PatternDialog.jsx";
import FacultyDialog from "./dialogs/FacultyDialog.jsx";

import { loadConfiguration, loadEmptyConfig } from "../../components/APICommunication";

export default function ConfigEditor() {
  const { state, loading } = useAppState();
  const config = state?.config;
  const [doc, setDoc] = useState(null);
  const [loadingFile, setLoadingFile] = useState(false);
  const revision = config?.revision;
  const hasConfig = Boolean(config) && config.status !== "none";
  const fileInputRef = useRef(null)
  const [editing, setEditing] = useState(null);   // editing used for dialog (not implemented)
  const [options, setOptions] = useState(null);   // library choices for the dialogs; they have fallbacks

  const Empty_Click = async () => {

    setLoadingFile(true);

    try {
      const res = await loadEmptyConfig();

      return res.json();
    } catch (error) {
      return error;

    } finally {
      await new Promise(resolve => setTimeout(resolve, 2000));
      setLoadingFile(false);
    }
  }


  useEffect(() => {
    if (!hasConfig) return;
    api.config.get().then((reply) => {
      setDoc({ document: reply.document, sections: reply.sections });
    });
  }, [hasConfig, revision]);

  useEffect(() => {
    api.config.options().then(setOptions).catch(() => { });   // the dialogs' fallbacks cover a failure
  }, []);

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
              <Button variant="primary" onClick={() => Empty_Click()}>New</Button>
              <Button onClick={() => { fileInputRef.current.click(); }}>Load JSON...</Button>
              <input
                ref={fileInputRef}
                type="file"
                style={{ display: "none" }}
                onChange={async (event) => {
                  setLoadingFile(true);
                  const file = event.target.files[0];
                  if (!file) return;
                  try {
                    const res = await loadConfiguration(file);

                    if (!res.ok) {
                      const errorText = await res.text();
                      console.log("Server response:", errorText);
                      throw new Error(errorText);
                    }

                    else {
                      return res.json();
                    }
                  } catch (err) {
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
            <Button onClick={Empty_Click}>New</Button>

            <Button onClick={() => fileInputRef.current.click()}>Load JSON...</Button>
            <input
              ref={fileInputRef}
              type="file"
              style={{ display: "none" }}
              onChange={async (event) => {
                setLoadingFile(true);
                const file = event.target.files[0];
                if (!file) return;
                try {
                  const res = await loadConfiguration(file);
                  if (!res.ok) {
                    //	config.status = "none";
                    throw new Error("Invalid configuration file");
                  } else {
                    //	config.status = "valid";
                    return res.json();
                  }
                } catch (err) {
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
          <CardRow
            title="Faculty"
            meta={items.faculty.length}
            addLabel="Add faculty"
            onAdd={() => setEditing({ area: "faculty", index: null })}
          >
            {items.faculty.map((f, i) => (

              <FacultyCard
                key={i}
                faculty={f}
                onEdit={() => setEditing({ area: "faculty", index: i })}
              />
            ))}
          </CardRow>
          <CardRow
            title="Courses"
            meta={plural(items.courses.length, "section")}
            addLabel="Add course"
            onAdd={() => setEditing({ area: "courses", index: null })}
          >
            {items.courses.map((c, i) => (
              <CourseCard
                key={i}
                course={c}
                label={doc.sections[i]}

                onEdit={() => setEditing({ area: "courses", index: i })}

              />
            ))}
          </CardRow>
          <div className="editor-pair">

            <CardRow
              title="Rooms"
              meta={items.rooms.length}
              addLabel="Add room"
              onAdd={() => setEditing({ area: "rooms", index: null })}
            >
              {items.rooms.map((r, i) => (
                <ResourceCard
                  key={i}
                  resource={r}
                  usedBy={items.courses.filter((c) => c.room.includes(r.name)).length}
                  onEdit={() => setEditing({ area: "rooms", index: i })}
                />
              ))}
            </CardRow>
            <CardRow
              title="Labs"
              meta={items.labs.length}
              addLabel="Add lab"
              onAdd={() => setEditing({ area: "labs", index: null })}
            >
              {items.labs.map((l, i) => (
                <ResourceCard
                  key={i}
                  resource={l}
                  usedBy={items.courses.filter((c) => c.lab.includes(l.name)).length}
                  onEdit={() => setEditing({ area: "labs", index: i })}
                />
              ))}
            </CardRow>
          </div>
          <CardRow
            title="Class Patterns"
            meta={`${enabled} of ${patterns.length} enabled`}
            addLabel="Add pattern"
            onAdd={() => setEditing({ area: "patterns", index: null })}
          >
            {patterns.map((p, i) => (
              <PatternCard
                key={i}
                pattern={p}
                onEdit={() => setEditing({ area: "patterns", index: i })} />
            ))}
          </CardRow>
          {/* Later: TimeSlotsCard and SettingsCard (edit-only, not part of this pass) */}
          {editing?.area === "faculty" && (
            <FacultyDialog
              key={`faculty-${editing.index}`}
              index={editing.index}
              faculty={editing.index === null ? null : items.faculty[editing.index]}
              courseIds={[...new Set(items.courses.map((c) => c.course_id))]}
              rooms={items.rooms.map((r) => r.name)}
              labs={items.labs.map((l) => l.name)}
              options={options}
              onCancel={() => setEditing(null)}
              onSave={(draft) => console.log("save", editing, draft)}   /* For testing, Eman replaces this */
            />
          )}
          {editing?.area === "courses" && (
            <CourseDialog
              key={`courses-${editing.index}`}
              index={editing.index}
              course={editing.index === null ? null : items.courses[editing.index]}
              label={editing.index === null ? null : doc.sections[editing.index]}
              rooms={items.rooms.map((r) => r.name)}
              labs={items.labs.map((l) => l.name)}
              faculty={items.faculty.map((f) => f.name)}
              courseIds={[...new Set(items.courses.map((c) => c.course_id))]}
              roomFeatures={[...new Set(items.rooms.flatMap((r) => r.features ?? []))]}
              labFeatures={[...new Set(items.labs.flatMap((l) => l.features ?? []))]}
              options={options}
              onCancel={() => setEditing(null)}
              onSave={(draft) => console.log("save", editing, draft)}   /* For testing, Eman replaces this */
            />
          )}
          {(editing?.area === "rooms" || editing?.area === "labs") && (
            <ResourceDialog
              key={`${editing.area}-${editing.index}`}
              area={editing.area}
              index={editing.index}
              resource={editing.index === null ? null : items[editing.area][editing.index]}
              suggestions={[...new Set(items[editing.area].flatMap((r) => r.features ?? []))]}
              onCancel={() => setEditing(null)}
              onSave={(draft) => console.log("save", editing, draft)}   /* For testing, Eman replaces this */
            />
          )}
          {editing?.area === "patterns" && (
            <PatternDialog
              key={`patterns-${editing.index}`}
              index={editing.index}
              pattern={editing.index === null ? null : patterns[editing.index]}
              options={options}
              onCancel={() => setEditing(null)}
              onSave={(draft) => console.log("save", editing, draft)}   /* Eman replaces this */
            />
          )}
        </>
      )}
    </div>
  );
}
