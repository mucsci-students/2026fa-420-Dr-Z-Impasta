/**
 * Weekly timetable: one column per day, events positioned by their times.
 * Overlapping events (common in the faculty view or when a schedule has a
 * conflict) are placed side by side in lanes.
 */
import { DAYS, END_HOUR, START_HOUR, formatMinutes } from "./scheduleData.js";

const HOUR_HEIGHT = 52; // px per hour; keep in sync with nothing else — it's all inline
const DAY_START = START_HOUR * 60;
const DAY_END = END_HOUR * 60;

function isPlaceable(event) {
  return (
    DAYS.includes(event.day) &&
    event.start != null &&
    event.end != null &&
    event.end > event.start &&
    event.end > DAY_START &&
    event.start < DAY_END
  );
}

/**
 * Assigns each event a lane. Events that overlap form a cluster, and every
 * event in a cluster shares its width equally with the others.
 */
function layoutDay(events) {
  const sorted = [...events].sort((a, b) => a.start - b.start || a.end - b.end);
  const placed = [];
  let cluster = [];
  let laneEnds = [];
  let clusterEnd = -1;

  function flush() {
    cluster.forEach((item) => {
      item.lanes = laneEnds.length;
    });
    placed.push(...cluster);
    cluster = [];
    laneEnds = [];
    clusterEnd = -1;
  }

  sorted.forEach((event) => {
    if (cluster.length && event.start >= clusterEnd) flush();

    let lane = laneEnds.findIndex((end) => end <= event.start);
    if (lane === -1) {
      lane = laneEnds.length;
      laneEnds.push(event.end);
    } else {
      laneEnds[lane] = event.end;
    }

    cluster.push({ event, lane, lanes: 1 });
    clusterEnd = Math.max(clusterEnd, event.end);
  });
  flush();

  return placed;
}

function eventStyle({ event, lane, lanes }) {
  const start = Math.max(event.start, DAY_START);
  const end = Math.min(event.end, DAY_END);
  return {
    top: ((start - DAY_START) / 60) * HOUR_HEIGHT,
    height: ((end - start) / 60) * HOUR_HEIGHT,
    left: `calc(${(lane / lanes) * 100}% + 3px)`,
    width: `calc(${100 / lanes}% - 6px)`,
  };
}

export default function Timetable({ events, groupBy }) {
  const hours = [];
  for (let hour = START_HOUR; hour < END_HOUR; hour += 1) hours.push(hour);

  const placeable = events.filter(isPlaceable);
  const unplaced = events.length - placeable.length;

  return (
    <>
      <div className="timetable">
        <div className="timetable__grid">
          <div className="timetable__head">
            <div />
            {DAYS.map((day) => (
              <div key={day} className="timetable__day-name">
                {day}
              </div>
            ))}
          </div>

          <div className="timetable__body">
            <div className="timetable__times">
              {hours.map((hour) => (
                <div key={hour} className="timetable__time" style={{ height: HOUR_HEIGHT }}>
                  {String(hour).padStart(2, "0")}:00
                </div>
              ))}
            </div>

            {DAYS.map((day) => (
              <div
                key={day}
                className="timetable__column"
                style={{
                  height: hours.length * HOUR_HEIGHT,
                  backgroundSize: `100% ${HOUR_HEIGHT}px`,
                }}
              >
                {layoutDay(placeable.filter((event) => event.day === day)).map((item) => {
                  const { event } = item;
                  const detail =
                    groupBy === "faculty" ? event.place : event.faculty;
                  const time = `${formatMinutes(event.start)}–${formatMinutes(event.end)}`;

                  return (
                    <div
                      key={event.id}
                      className={`timetable__event${event.isLab ? " timetable__event--lab" : ""}`}
                      style={eventStyle(item)}
                      title={[`${event.courseId}.${event.sectionId}`, detail, time]
                        .filter(Boolean)
                        .join(" · ")}
                    >
                      <strong>
                        {event.courseId}
                        {event.sectionId && (
                          <span className="timetable__section"> .{event.sectionId}</span>
                        )}
                      </strong>
                      {detail && <span className="timetable__detail">{detail}</span>}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      {unplaced > 0 && (
        <p className="muted">
          {unplaced === 1 ? "1 meeting has" : `${unplaced} meetings have`} no usable day or
          time and {unplaced === 1 ? "isn't" : "aren't"} shown on the timetable. Switch to
          Table to see {unplaced === 1 ? "it" : "them"}.
        </p>
      )}
    </>
  );
}