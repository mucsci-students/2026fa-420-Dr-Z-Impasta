"""Print the current scheduler configuration in human-readable form.

Author: Foster VanFleet
Date: September 16th, 2026
"""

from zimpasta.console import Console
from zimpasta.session import Session


def print_config(console: Console, session: Session) -> None:
    """Print the current configuration in a human-readable format."""
    if not session.has_config:
        console.say("No configuration is loaded.")
        return

    config = session.config
    scheduler_config = config.config

    console.say("Configuration")
    console.say("=============")

    console.say("")
    console.say("Rooms")
    console.say("-----")
    for room in scheduler_config.rooms:
        console.say(f"{room.name}")
        console.say(f"  Capacity: {room.capacity}")

        features = ", ".join(room.features) if room.features else "None"
        console.say(f"  Features: {features}")

    console.say("")
    console.say("Labs")
    console.say("----")
    for lab in scheduler_config.labs:
        console.say(f"{lab.name}")
        console.say(f"  Capacity: {lab.capacity}")

        features = ", ".join(lab.features) if lab.features else "None"
        console.say(f"  Features: {features}")

    console.say("")
    console.say("Courses")
    console.say("-------")
    for course in scheduler_config.courses:
        console.say(f"{course.course_id}")
        console.say(f"  Credits: {course.credits}")
        console.say(f"  Capacity: {course.capacity}")

        rooms = ", ".join(course.room) if course.room else "None"
        console.say(f"  Rooms: {rooms}")

        labs = ", ".join(course.lab) if course.lab else "None"
        console.say(f"  Labs: {labs}")

        conflicts = ", ".join(course.conflicts) if course.conflicts else "None"
        console.say(f"  Conflicts: {conflicts}")

        faculty = ", ".join(course.faculty) if course.faculty else "None"
        console.say(f"  Faculty: {faculty}")

    console.say("")
    console.say("Faculty")
    console.say("-------")
    for faculty in scheduler_config.faculty:
        console.say(f"{faculty.name}")
        console.say(
            f"  Credits: {faculty.minimum_credits}-{faculty.maximum_credits}"
        )
        console.say(f"  Unique course limit: {faculty.unique_course_limit}")

        console.say("  Availability:")
        for day, times in faculty.times.items():
            formatted_times = ", ".join(
                f"{time.start}-{time.end}" for time in times
            )
            console.say(f"    {day}: {formatted_times}")

    console.say("")
    console.say("Time Slots")
    console.say("----------")

    console.say("Available Times:")
    for day, time_blocks in config.time_slot_config.times.items():
        for time_block in time_blocks:
            console.say(
                f"  {day}: {time_block.start}-{time_block.end} "
                f"({time_block.spacing} minute spacing)"
            )

    console.say("")
    console.say("Class Patterns:")
    for class_pattern in config.time_slot_config.classes:
        console.say(f"  {class_pattern.credits} credits")

        for meeting in class_pattern.meetings:
            lab = ", lab" if meeting.lab else ""
            console.say(
                f"    {meeting.day}, {meeting.duration} minutes{lab}"
            )

    console.say("")
    console.say(
        f"Maximum time gap: {config.time_slot_config.max_time_gap} minutes"
    )
    console.say(
        f"Minimum time overlap: "
        f"{config.time_slot_config.min_time_overlap} minutes"
    )

    console.say("")
    console.say(f"Schedule Limit: {config.limit}")

    if config.optimizer_flags:
        flags = ", ".join(str(flag) for flag in config.optimizer_flags)
    else:
        flags = "None"

    console.say(f"Optimizer Flags: {flags}")
