"""Find configuration objects by type and identifier.

Author: Foster VanFleet
Date: September 16th, 2026
"""

from scheduler import (
    CombinedConfig,
    CourseConfig,
    FacultyConfig,
    LabConfig,
    RoomConfig,
)


class ConfigFinder:
    """Find configuration objects within a scheduler configuration."""

    def __init__(self, config: CombinedConfig) -> None:
        self.config = config

    def parse_config(
        self,
        config_type: (
            type[CourseConfig] | type[FacultyConfig] | type[LabConfig] | type[RoomConfig]
        ),
        identifier: str,
    ) -> list[CourseConfig] | list[FacultyConfig] | list[LabConfig] | list[RoomConfig]:
        if config_type is CourseConfig:
            return [
                course for course in self.config.config.courses if course.course_id == identifier
            ]

        if config_type is FacultyConfig:
            return [faculty for faculty in self.config.config.faculty if faculty.name == identifier]

        if config_type is RoomConfig:
            return [room for room in self.config.config.rooms if room.name == identifier]

        if config_type is LabConfig:
            return [lab for lab in self.config.config.labs if lab.name == identifier]

        raise TypeError(f"Unsupported configuration type: {config_type}")
