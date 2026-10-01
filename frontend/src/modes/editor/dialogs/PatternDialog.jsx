// Description:
// | Field                 | Control                 | Notes
// | credits               | number, required        |
// | disabled              | switch (Enabled)        | Inverted: switch on = disabled: false.
// |                       |                         | Show the word too, not just the switch
// | start_time            | time, optional          | Empty = null ("Any start time")
// | meetings              | list, add/remove rows   | Required; one row per meeting
// | meetings[].day        | select (weekdays)       | Options from api.config.options()
// | meetings[].duration   | number, required        | Minutes
// | meetings[].lab        | checkbox                | One lab meeting per pattern; the library
// |                       |                         | reports it, don't check in JS
// | meetings[].delivery   | select (delivery modes) | Defaults to in_person
// | meetings[].start_time | time, optional          | Overrides the pattern's start_time
