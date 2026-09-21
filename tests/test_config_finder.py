"""Test finding configuration objects by type and identifier.

Author: Foster VanFleet
Date: September 16th, 2026
"""

import pytest
from scheduler import CourseConfig, FacultyConfig, LabConfig, RoomConfig

from zimpasta.config_finder import ConfigFinder


def test_find_course(config) -> None:
    finder = ConfigFinder(config)

    result = finder.parse_config(CourseConfig, "CS 101")

    assert len(result) == 1
    assert result[0].course_id == "CS 101"


def test_find_missing_course(config) -> None:
    finder = ConfigFinder(config)

    result = finder.parse_config(CourseConfig, "CS 999")

    assert result == []


def test_find_faculty(config) -> None:
    finder = ConfigFinder(config)

    result = finder.parse_config(FacultyConfig, "Dr. Smith")

    assert len(result) == 1
    assert result[0].name == "Dr. Smith"


def test_find_room(config) -> None:
    finder = ConfigFinder(config)

    result = finder.parse_config(RoomConfig, "Room 101")

    assert len(result) == 1
    assert result[0].name == "Room 101"


def test_find_lab(config) -> None:
    finder = ConfigFinder(config)

    result = finder.parse_config(LabConfig, "Lab 101")

    assert len(result) == 1
    assert result[0].name == "Lab 101"


def test_find_multiple_matches(config) -> None:
    config.config.courses.append(config.config.courses[0])

    finder = ConfigFinder(config)

    result = finder.parse_config(CourseConfig, "CS 101")

    assert len(result) == 2
    assert result[0].course_id == "CS 101"
    assert result[1].course_id == "CS 101"


def test_unsupported_config_type(config) -> None:
    finder = ConfigFinder(config)

    with pytest.raises(TypeError):
        finder.parse_config(str, "CS 101")
