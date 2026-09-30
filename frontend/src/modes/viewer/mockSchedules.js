/**
 * Development-only mock schedules, in the real JSONWriter format.
 *
 * Shown only on localhost / 127.0.0.1 when the URL has ?mock in it, so the
 * deployed site and normal runs always use real data (or the empty state).
 * Delete this file once the viewer works against real generated schedules.
 */

export function mockRequested() {
  if (typeof window === "undefined") return false;
  const { hostname, search } = window.location;
  const isLocal = hostname === "localhost" || hostname === "127.0.0.1";
  return isLocal && new URLSearchParams(search).has("mock");
}

/* Helpers so the mock stays readable: t(day 1–5, "HH:MM", minutes). */
function t(day, clock, duration, delivery = "in_person") {
  const [hours, minutes] = clock.split(":").map(Number);
  return { day, start: hours * 60 + minutes, duration, delivery };
}
const MWF = (clock, duration) => [t(1, clock, duration), t(3, clock, duration), t(5, clock, duration)];
const TR = (clock, duration) => [t(2, clock, duration), t(4, clock, duration)];

export const MOCK_SCHEDULES = {
  source: "generated",
  created_at: new Date().toISOString(),
  name: "mock_config.json",
  items: [
    [
      { course: "CMSC 340.01", faculty: "Yang", room: "Roddy 136", times: MWF("10:00", 50) },
      {
        course: "CMSC 161.01",
        faculty: "Zoppetti",
        room: "Roddy 136",
        lab: "Linux",
        times: [...MWF("12:00", 50), t(4, "14:00", 110)],
        lab_index: 3,
        reserve_room_during_lab: false,
      },
      { course: "CMSC 362.01", faculty: "Zoppetti", room: "Roddy 136", times: TR("14:00", 75) },
      {
        course: "CMSC 161.02",
        faculty: "Girard",
        room: "Roddy 140",
        lab: "Mac",
        times: [...TR("09:30", 75), t(3, "13:00", 110)],
        lab_index: 2,
        reserve_room_during_lab: true,
      },
      { course: "CMSC 476.01", faculty: "Yang", room: "Roddy 147", times: TR("17:00", 120) },
      // Overlaps CMSC 362 on Tuesday — shows side-by-side lanes in the faculty view.
      { course: "CMSC 420.01", faculty: "Zoppetti", room: "Roddy 140", times: [t(2, "14:30", 75)] },
      { course: "CMSC 150.01", faculty: "Girard", times: [t(1, "18:00", 150, "online")] },
    ],
    [
      { course: "CMSC 340.01", faculty: "Yang", room: "Roddy 140", times: MWF("08:00", 50) },
      {
        course: "CMSC 161.01",
        faculty: "Zoppetti",
        room: "Roddy 136",
        lab: "Linux",
        times: [...TR("11:00", 75), t(5, "13:00", 110)],
        lab_index: 2,
        reserve_room_during_lab: false,
      },
    ],
  ],
};