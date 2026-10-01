// Description: One tile per weekday listing its blocks (start–end, spacing).
//
// | Field           | Control        | Notes
// | limit           | number         | Max schedules per run
// | optimizer_flags | 7 toggle chips | From api.config.options(); use each
// |                 |                | flag's description as its tooltip
//
// Missing From Mockup: Max time gap (max_time_gap, default 30) and Min overlap
// (min_time_overlap, default 45). The mockup hides them behind "Advanced timing options…", so add
// a small line like Gap 30m · Overlap 45m in the header or under the tiles. Then they're visible
// without opening the dialog.
