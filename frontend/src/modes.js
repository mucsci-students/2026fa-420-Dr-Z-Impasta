/** The three modes, in navigation order. Each has its own folder under src/modes/. */
export const MODES = [
  {
    path: "/editor",
    number: "01",
    label: "Configuration Editor",
    description: "Create, load, edit, validate, and save a scheduler configuration.",
  },
  {
    path: "/generator",
    number: "02",
    label: "Schedule Generator",
    description: "Generate schedules from the last validated configuration.",
  },
  {
    path: "/viewer",
    number: "03",
    label: "Schedule Viewer",
    description: "Browse, load, and export generated schedules by room or faculty.",
  },
];
