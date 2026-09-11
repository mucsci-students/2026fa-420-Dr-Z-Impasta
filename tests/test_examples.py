from scheduler import CombinedConfig, Scheduler

from tests.conftest import SAMPLE_CONFIG


def test_sample_config_exists_and_validates(config: CombinedConfig):
    assert SAMPLE_CONFIG.is_file()
    assert config.limit == 3
    assert [course.course_id for course in config.config.courses] == ["CS 101", "CS 102"]


def test_sample_config_is_solvable(config: CombinedConfig):
    schedules = list(Scheduler(config, solver_timeout_ms=10_000).get_models())

    assert len(schedules) == config.limit
