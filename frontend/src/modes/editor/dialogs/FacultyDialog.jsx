// Description:
// |     Field           |       Control	    |              Notes
// | name	             | text, required	    |
// | minimum_credits	 | number, required	    |
// | maximum_credits	 | number, required	    |
// | unique_course_limit | number, required	    |
// | maximum_days	     | number (min=0 max=5) | Optional; defaults to 5
// | times	             | AvailabilityEditor	| Required. An empty day means unavailable
// | mandatory_days	     | Mo–Fr checkboxes	    |
// | course_preferences	 | PreferenceEditor	    | Pick from the course IDs in the document, plus an 
// |                     |                      | integer score
// | room_preferences	 | PreferenceEditor	    | Pick from room names
// | lab_preferences	 | PreferenceEditor	    | Pick from lab names
