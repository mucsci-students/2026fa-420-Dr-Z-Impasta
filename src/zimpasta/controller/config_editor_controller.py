from zimpasta.controller import AppController
from zimpasta.model.export import ExportFormat, resolve_output_path
from zimpasta.model.workspace import ConfigStatus


class ConfigEditorController:
    REVISION_COUNTER = 0
    CURR_FILENAME = ""
    EXP_FORMAT = ExportFormat.parse("json")
    CURR_FILE = None

    def __init__(self, app: AppController) -> None:
        self.app = app
        self.workspace = app.workspace

    def load_json(self, filename: str, content: str) -> ConfigStatus:
        """Runs when the submit button is clicked from the Load JSON operation
        Returns the status of the loaded file: VALID = "valid",
        INCOMPLETE = "incomplete", or NONE = "none"""
        self.CURR_FILENAME = filename
        self.CURR_FILE = config_doc["document"]
        config_doc = self.app.load_configuration(self.CURR_FILENAME, content)

        return config_doc["state"]["status"]

    def save_json(self, path: str) -> bool:
        """Runs when the Save Json button is clicked, saves the current config file to path
        Returns True if file was saved successfully and False otherwise"""
        self.REVISION_COUNTER += 1

        config_state_snapshot = self.app.mark_configuration_saved(
            self.REVISION_COUNTER, self.CURR_FILENAME
        )

        if config_state_snapshot["status"] == ConfigStatus.VALID:
            export_file = self.app.export_configuration()
            path_name = resolve_output_path(path, self.EXP_FORMAT)

            try:
                path_name.write_text(export_file.content, encoding="utf-8")
            except OSError:
                return False
            return True
        else:
            return False

    def validate_config(self) -> bool:
        """Runs when the Validate button is clicked
        Returns True if validate was successful and False otherwise"""
        report = self.app.validate_configuration()

        if report["report"]["status"] == "valid":
            return True
        return False

    def delete_item(self, area: str, index: int) -> list[tuple[str, str]]:
        """Runs when an attribute's delete button is clicked
        Returns either an empty list, if the deletetion would have no blockers
        or a list of tuples of the blocking field's value & field name

        For example, trying to delete Roddy 136 would return
        [('CMSC 161.01', 'room'), ('CMSC 362.01', 'room'),...]"""
        impact = self.app.delete_impact(area, index)
        if impact["blocking"] == []:
            self.app.delete_item(area, index)
            return []

        blockers = []
        for block in impact["blocking"]:
            blockers.append({block["label"], block["field"]})
        return blockers

    def validate_apply_item(self, section: str, area: str, values: list[tuple]) -> None:
        allowed = allowed_keys(section)
        change = self.workspace._update_section(section, area, allowed, values)
        print(change)
        return None

    def allowed_keys(section: str) -> None:
        return None
