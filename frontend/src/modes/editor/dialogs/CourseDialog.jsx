// Description:
// | Field                   | Control                   | Notes
// | course_id               | text, required            | Repeating an ID creates another section
// | section_id              | text, optional            | Blank = null, which auto-numbers (.01, .02…)
// | credits                 | number, required          |
// | capacity                | number, required          |
// | room                    | multi-select (rooms)      | Can be empty (e.g. online courses)
// | lab                     | multi-select (labs)       | Empty = no lab meeting
// | conflicts               | multi-select (course IDs) | Unique base IDs (CMSC 161), not section labels
// | faculty                 | radio: Any / Specific     | Any = null: candidates come from faculty
// |                         |                           | course preferences. Specific shows a
// |                         |                           | multi-select of faculty names
// | modality                | select (modalities)       | Options from api.config.options();
// |                         |                           | defaults to in_person
// | required_room_features  | TagInput                  | Suggest tags existing rooms already have
// | required_lab_features   | TagInput                  | Suggest tags existing labs already have
// | reserve_room_during_lab | checkbox, default on      | Only matters when lab isn't empty
//
// Applies to All Dialogs: The availability editor serves three cards. Faculty, rooms and labs all
// use the same per-day times shape, so the shared AvailabilityEditor.jsx covers all of them. Rooms
// and labs also need an "Always available" choice that sets times to null. For faculty, an empty
// day just means unavailable.