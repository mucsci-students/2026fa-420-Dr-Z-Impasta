// Description:
// | Field                | Control               | Notes
// | times[DAY]           | list, add/remove rows | Each weekday needs at least one block; the
// |                      |                       | library reports an empty one. Saving sends
// |                      |                       | the whole times object, not just this day
// | times[DAY][].start   | time, required        |
// | times[DAY][].end     | time, required        |
// | times[DAY][].spacing | number (minutes)      | Minutes between slots
