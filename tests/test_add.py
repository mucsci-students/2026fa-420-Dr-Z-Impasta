"""Comprehensive tests for zimpasta/commands/add.py.

Covers core happy paths, error cases, interactive builders, and exhaustive
edge-case validation constraints.
"""

import unittest

from zimpasta.command import CommandError
from zimpasta.commands.add import add_spec
from zimpasta.session import Session


class FakeCombinedConfig:
    """Stands in for scheduler.CombinedConfig."""

    def __init__(self):
        self.rooms = {}
        self.labs = {}
        self.courses = {}
        self.faculty = {}

    def edit_mode(self):
        return _EditMode(self)


class _EditMode:
    def __init__(self, config):
        self._config = config

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def add_room(self, name, capacity):
        if capacity < 0:
            raise ValueError("Capacity cannot be negative.")
        if name in self._config.rooms:
            raise ValueError(f"Room '{name}' already exists.")
        self._config.rooms[name] = {"capacity": capacity}

    def add_lab(self, name, capacity):
        if capacity < 0:
            raise ValueError("Capacity cannot be negative.")
        if name in self._config.labs:
            raise ValueError(f"Lab '{name}' already exists.")
        self._config.labs[name] = {"capacity": capacity}

    def add_course(self, course_id, credits, capacity):
        if credits < 0 or capacity < 0:
            raise ValueError("Credits and capacity cannot be negative.")
        if course_id in self._config.courses:
            raise ValueError(f"Course '{course_id}' already exists.")
        self._config.courses[course_id] = {"credits": credits, "capacity": capacity}

    def add_faculty(self, name, maximum_credits, minimum_credits, unique_course_limit):
        if name in self._config.faculty:
            raise ValueError(f"Faculty '{name}' already exists.")
        self._config.faculty[name] = {
            "maximum_credits": maximum_credits,
            "minimum_credits": minimum_credits,
            "unique_course_limit": unique_course_limit,
        }


class Console:
    """Simple console stub for testing interactive prompts and output."""

    def __init__(self, answers=()):
        self._answers = list(answers)
        self.said = []

    def ask(self, prompt):
        self.said.append(("ask", prompt))
        if not self._answers:
            return ""
        return self._answers.pop(0)

    def say(self, message):
        self.said.append(("say", message))


def make_session():
    return Session(config=FakeCombinedConfig())


class TestAddHappyPaths(unittest.TestCase):
    def test_add_room_works(self):
        session = make_session()
        add_spec.handler(Console(), session, add_spec.parse(["room", "R1", "--capacity", "28"]))
        self.assertEqual(session.config.rooms["R1"], {"capacity": 28})

    def test_add_lab_works(self):
        session = make_session()
        add_spec.handler(Console(), session, add_spec.parse(["lab", "L1", "--capacity", "20"]))
        self.assertEqual(session.config.labs["L1"], {"capacity": 20})

    def test_add_course_works(self):
        session = make_session()
        add_spec.handler(
            Console(),
            session,
            add_spec.parse(["course", "CS101", "--credits", "4", "--capacity", "28"]),
        )
        self.assertEqual(session.config.courses["CS101"], {"credits": 4, "capacity": 28})

    def test_add_faculty_works(self):
        session = make_session()
        add_spec.handler(
            Console(),
            session,
            add_spec.parse(
                [
                    "faculty",
                    "Doe",
                    "--maximum-credits",
                    "12",
                    "--minimum-credits",
                    "12",
                    "--unique-course-limit",
                    "2",
                ]
            ),
        )
        self.assertEqual(
            session.config.faculty["Doe"],
            {"maximum_credits": 12, "minimum_credits": 12, "unique_course_limit": 2},
        )


class TestAddErrorsAndEdgeCases(unittest.TestCase):
    def test_no_config_loaded_raises(self):
        session = Session()  # config is None
        with self.assertRaises(CommandError):
            add_spec.handler(Console(), session, add_spec.parse(["room", "R1", "--capacity", "28"]))

    def test_missing_required_option_raises(self):
        session = make_session()
        with self.assertRaises(CommandError):
            add_spec.handler(Console(), session, add_spec.parse(["room", "R1"]))

    def test_duplicate_id_raises(self):
        session = make_session()
        invocation = add_spec.parse(["room", "R1", "--capacity", "28"])
        add_spec.handler(Console(), session, invocation)
        with self.assertRaises(CommandError):
            add_spec.handler(Console(), session, invocation)

    def test_non_integer_capacity_raises_command_error(self):
        session = make_session()
        with self.assertRaises(CommandError) as ctx:
            add_spec.handler(
                Console(), session, add_spec.parse(["room", "R1", "--capacity", "not-a-number"])
            )
        self.assertIn("must be a whole number", str(ctx.exception))

    def test_float_string_capacity_raises_command_error(self):
        session = make_session()
        with self.assertRaises(CommandError):
            add_spec.handler(
                Console(), session, add_spec.parse(["room", "R1", "--capacity", "25.5"])
            )


class TestAddBuilder(unittest.TestCase):
    def test_bare_add_prompts_and_completes(self):
        console = Console(answers=["room", "R1", "28"])
        built = add_spec.builder(console, make_session(), add_spec.parse([]))
        self.assertTrue(built.complete)
        self.assertEqual(built.get("id"), "R1")
        self.assertEqual(built.get("capacity"), "28")

    def test_builder_empty_id_returns_none(self):
        console = Console(answers=["room", "", "30"])
        built = add_spec.builder(console, make_session(), add_spec.parse([]))
        self.assertIsNone(built)
        self.assertTrue(any("id is required" in msg[1] for msg in console.said if msg[0] == "say"))


if __name__ == "__main__":
    unittest.main()
