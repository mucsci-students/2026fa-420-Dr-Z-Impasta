"""The shipped example must stay a valid, solvable configuration."""

import json

from scheduler import CombinedConfig, Scheduler

from tests.helpers import EXAMPLE_CONFIG, FIXTURE_CONFIG


def test_example_config_validates():
    data = json.loads(EXAMPLE_CONFIG.read_text(encoding="utf-8"))

    config = CombinedConfig.model_validate(data)

    assert config.config.courses and config.config.faculty
    assert config.config.rooms and config.config.labs


def test_example_config_is_solvable():
    data = json.loads(EXAMPLE_CONFIG.read_text(encoding="utf-8"))
    data["limit"] = 1

    config = CombinedConfig.model_validate(data)
    schedules = list(Scheduler(config, solver_timeout_ms=60_000).get_models())

    assert len(schedules) == 1
    assert {instance.course_str.split(".")[0] for instance in schedules[0]} == {
        course.course_id for course in config.config.courses
    }


def test_fixture_config_is_small_and_solvable():
    config = CombinedConfig.model_validate(json.loads(FIXTURE_CONFIG.read_text(encoding="utf-8")))

    assert [course.course_id for course in config.config.courses] == ["CS 101", "CS 102"]
    assert len(list(Scheduler(config, solver_timeout_ms=10_000).get_models())) == config.limit
