"""Tests for zimpasta/commands/add.py, using field names from sample_config.json.

scheduler.CombinedConfig is faked here since its real API isn't confirmed yet --
FakeCombinedConfig mirrors the *assumed* method signatures noted in add.py's TODO:
add_room(name, capacity), add_lab(name, capacity), add_course(course_id, credits,
capacity), add_faculty(name, maximum_credits, minimum_credits, unique_course_limit),
each raising ValueError on a duplicate id.
"""

import unittest

from zimpasta.command import CommandError
from zimpasta.commands.add import KINDS, add_spec
from zimpasta.session import Session


class FakeCombinedConfig:
    """Minimal double for scheduler.CombinedConfig, just enough to exercise add.py."""

    def __init__(self):
        self.rooms = {}
        self.labs = {}
        self.courses = {}
        self.faculty = {}

    def edit_mode(self):
        return _EditModeContext(self)


class _FakeEditProxy:
    def __init__(self, config: FakeCombinedConfig):
        self._config = config

    def add_room(self, name, capacity):
        if name in self._config.rooms:
            raise ValueError(f"Room '{name}' already exists.")
        self._config.rooms[name] = {"capacity": capacity}

    def add_lab(self, name, capacity):
        if name in self._config.labs:
            raise ValueError(f"Lab '{name}' already exists.")
        self._config.labs[name] = {"capacity": capacity}

    def add_course(self, course_id, credits, capacity):
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


class _EditModeContext:
    def __init__(self, config: FakeCombinedConfig):
        self._config = config

    def __enter__(self):
        return _FakeEditProxy(self._config)

    def __exit__(self, exc_type, exc, tb):
        return False  # never swallow exceptions


class FakeConsole:
    """Feeds canned answers to .ask() in order; records everything said."""

    def __init__(self, answers=()):
        self._answers = list(answers)
        self.said = []

    def ask(self, prompt):
        self.said.append(("ask", prompt))
        return self._answers.pop(0)

    def say(self, message):
        self.said.append(("say", message))


def make_session(loaded=True):
    return Session(config=FakeCombinedConfig()) if loaded else Session()


class TestAddSpecShape(unittest.TestCase):
    def test_verb_and_positionals(self):
        self.assertEqual(add_spec.verb, "add")
        self.assertIsNone(add_spec.noun)
        self.assertEqual([p.name for p in add_spec.positionals], ["kind", "id"])
        self.assertEqual(add_spec.positionals[0].choices, KINDS)

    def test_declares_all_kind_specific_options(self):
        option_names = {o.name for o in add_spec.options}
        self.assertEqual(
            option_names,
            {"capacity", "credits", "maximum-credits", "minimum-credits", "unique-course-limit"},
        )
        # None are required at the spec level -- see add.py's docstring for why.
        self.assertTrue(all(not o.required for o in add_spec.options))


class TestAddRequiresConfig(unittest.TestCase):
    def test_raises_when_nothing_is_loaded(self):
        console = FakeConsole()
        session = make_session(loaded=False)
        invocation = add_spec.parse(["room", "R1", "--capacity", "28"])
        with self.assertRaises(CommandError):
            add_spec.handler(console, session, invocation)


class TestAddRoom(unittest.TestCase):
    def test_one_liner_adds_room(self):
        console = FakeConsole()
        session = make_session()
        invocation = add_spec.parse(["room", "Roddy 999", "--capacity", "28"])

        add_spec.handler(console, session, invocation)

        self.assertEqual(session.config.rooms["Roddy 999"], {"capacity": 28})
        self.assertIn(("say", "Added room 'Roddy 999'."), console.said)

    def test_missing_capacity_raises_a_clear_error(self):
        console = FakeConsole()
        session = make_session()
        invocation = add_spec.parse(["room", "Roddy 999"])  # no --capacity

        with self.assertRaises(CommandError):
            add_spec.handler(console, session, invocation)

    def test_non_numeric_capacity_raises(self):
        console = FakeConsole()
        session = make_session()
        invocation = add_spec.parse(["room", "Roddy 999", "--capacity", "lots"])

        with self.assertRaises(CommandError):
            add_spec.handler(console, session, invocation)


class TestAddLab(unittest.TestCase):
    def test_one_liner_adds_lab(self):
        console = FakeConsole()
        session = make_session()
        invocation = add_spec.parse(["lab", "Botany", "--capacity", "20"])

        add_spec.handler(console, session, invocation)

        self.assertEqual(session.config.labs["Botany"], {"capacity": 20})


class TestAddCourse(unittest.TestCase):
    def test_one_liner_adds_course_with_credits_and_capacity(self):
        console = FakeConsole()
        session = make_session()
        invocation = add_spec.parse(
            ["course", "CMSC 490", "--credits", "4", "--capacity", "28"]
        )

        add_spec.handler(console, session, invocation)

        self.assertEqual(
            session.config.courses["CMSC 490"], {"credits": 4, "capacity": 28}
        )

    def test_missing_either_field_raises(self):
        console = FakeConsole()
        session = make_session()
        invocation = add_spec.parse(["course", "CMSC 490", "--credits", "4"])  # no capacity

        with self.assertRaises(CommandError):
            add_spec.handler(console, session, invocation)


class TestAddFaculty(unittest.TestCase):
    def test_one_liner_adds_faculty(self):
        console = FakeConsole()
        session = make_session()
        invocation = add_spec.parse(
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
        )

        add_spec.handler(console, session, invocation)

        self.assertEqual(
            session.config.faculty["Doe"],
            {"maximum_credits": 12, "minimum_credits": 12, "unique_course_limit": 2},
        )


class TestAddDuplicates(unittest.TestCase):
    def test_duplicate_within_same_kind_raises(self):
        console = FakeConsole()
        session = make_session()
        invocation = add_spec.parse(["lab", "Linux", "--capacity", "28"])
        add_spec.handler(console, session, invocation)

        with self.assertRaises(CommandError):
            add_spec.handler(console, session, invocation)

    def test_same_id_different_kind_is_allowed(self):
        console = FakeConsole()
        session = make_session()
        add_spec.handler(console, session, add_spec.parse(["room", "101", "--capacity", "10"]))
        add_spec.handler(
            console, session, add_spec.parse(["course", "101", "--credits", "3", "--capacity", "10"])
        )
        self.assertIn("101", session.config.rooms)
        self.assertIn("101", session.config.courses)


class TestAddParsing(unittest.TestCase):
    def test_kind_is_lowercased_and_validated(self):
        invocation = add_spec.parse(["ROOM", "R1", "--capacity", "28"])
        self.assertEqual(invocation.get("kind"), "room")

    def test_invalid_kind_raises_command_error(self):
        with self.assertRaises(CommandError):
            add_spec.parse(["dorm", "R1"])

    def test_bare_add_is_incomplete(self):
        invocation = add_spec.parse([])
        self.assertFalse(invocation.complete)
        self.assertEqual(invocation.missing(), ("kind", "id"))

    def test_missing_capacity_option_does_not_count_as_incomplete(self):
        """Documents a framework limitation: Option.required can't vary by kind,
        so this spec looks 'complete' even without --capacity. _add() must catch it."""
        invocation = add_spec.parse(["room", "R1"])
        self.assertTrue(invocation.complete)


class TestAddBuilder(unittest.TestCase):
    def test_prompts_for_kind_id_and_capacity_when_bare(self):
        console = FakeConsole(answers=["room", "R100", "28"])
        session = make_session()
        invocation = add_spec.parse([])

        built = add_spec.builder(console, session, invocation)

        self.assertTrue(built.complete)
        self.assertEqual(built.get("kind"), "room")
        self.assertEqual(built.get("id"), "R100")
        self.assertEqual(built.get("capacity"), "28")

    def test_prompts_for_two_fields_for_a_course(self):
        console = FakeConsole(answers=["4", "28"])  # credits, then capacity
        session = make_session()
        invocation = add_spec.parse(["course", "CMSC 999"])  # kind+id given

        built = add_spec.builder(console, session, invocation)

        self.assertEqual(built.get("credits"), "4")
        self.assertEqual(built.get("capacity"), "28")

    def test_only_prompts_for_fields_still_missing(self):
        console = FakeConsole(answers=["28"])  # just capacity
        session = make_session()
        invocation = add_spec.parse(["course", "CMSC 999", "--credits", "4"])

        built = add_spec.builder(console, session, invocation)

        self.assertEqual(built.get("credits"), "4")
        self.assertEqual(built.get("capacity"), "28")

    def test_empty_id_cancels_instead_of_looping(self):
        console = FakeConsole(answers=["lab", "   "])
        session = make_session()
        invocation = add_spec.parse([])

        built = add_spec.builder(console, session, invocation)

        self.assertIsNone(built)


if __name__ == "__main__":
    unittest.main()