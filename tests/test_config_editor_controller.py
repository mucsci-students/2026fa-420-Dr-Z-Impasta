from zimpasta.controller import AppController
from zimpasta.controller.config_editor_controller import ConfigEditorController as controller
from zimpasta.model.workspace import ConfigStatus

CTRL = controller(AppController())


def get_content() -> str:
    with open(r"C:\Users\qunde\2026fa-420-Dr-Z-Impasta\examples\sample_config.json") as file:
        content = file.read()
    return content


def test_new_json_button() -> None:
    return None


def test_load_json_submit_button_valid() -> None:
    assert CTRL.load_json("sample_config.json", get_content()) == ConfigStatus.VALID
    assert CTRL.load_json("samble_config.json", get_content()) == ConfigStatus.VALID


def test_load_json_submit_button_invalid_file() -> None:
    """assert(CTRL.load_json_submit("sample_config.json", "hi")["code"]
    == "sample_config.json is not valid JSON")"""


def test_save_json_button() -> None:
    """assert(CTRL.save_json("hi") == False)"""
    assert CTRL.save_json(r"C:\Users\qunde\2026fa-420-Dr-Z-Impasta\examples") is True
    assert CTRL.save_json(r"C:\Users\qunde\2026fa-420-Dr-Z-Impasta\examples\a.json") is True

def test_validate_json_button() -> None:
    assert CTRL.validate_config() is True

def test_faculty_add_button() -> None:
    return None


def test_faculty_profile_click() -> None:
    return None


def test_faculty_profile_invalid_data_in_field() -> None:
    return None


def test_faculty_delete_button() -> None:
    return None


def test_faculty_cancel_button() -> None:
    return None


def test_faculty_x_button() -> None:
    return None


def test_faculty_add_course_preference_button() -> None:
    return None


def test_faculty_mandatory_days_buttons() -> None:
    return None


def test_faculty_validate_and_apply_button() -> None:
    return None


def test_course_add_button() -> None:
    return None


def test_course_profile_click() -> None:
    return None


def test_rooms_add_button() -> None:
    return None


def test_rooms_profile_click() -> None:
    return None


def test_class_patterns_add_button() -> None:
    return None


def test_class_patterns_profile_click() -> None:
    return None


def test_time_slots_add_button() -> None:
    return None


def test_time_slots_profile_click() -> None:
    return None
