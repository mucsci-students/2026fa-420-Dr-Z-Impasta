from zimpasta.controller import AppController
from zimpasta.model.workspace import ConfigWorkspace, ConfigStatus
from zimpasta.controller.errors import _respond, _status_for, _FILE_READ_CODES
import json

class ConfigEditorController:
    def __init__(self, app: AppController) -> None:
        self.app = app
        self.workspace = app.workspace

    """ Runs when the submit button is clicked from the Load JSON operation
        Returns a dict structured as:
        {
            "state": 
                    {
                        "status"            : ConfigStatus,
                        "name"              : str | None,
                        "revision"          : int,
                        "saved_revision"    : int,
                        "dirty"             : bool,
                        "changes"           : list[dict] (each dict is a representation of a Change object or [])
                        "issues"            : list[dict] (each dict is a representation of an Issue object or [])
                        "validated_at"      : datetime | None
                        "counts"            : dict[str, int]

                    }
            "document": dict | None
            "sections": list[str]
        } 
    """
    def load_json_submit(self, filename: str, content: str) -> dict:
        config_doc = self.app.load_configuration(filename, content)
        
        if(config_doc["state"]["status"] == ConfigStatus.VALID):
            return {
                        "code" : config_doc["state"]["status"],
                        "message" : {
                            "document": config_doc["document"],
                            "sections": config_doc["sections"],
                            },
                    }
        else:
            return json.loads(_respond(
                    _status_for(workspace.InvalidFile()), 
                    _FILE_READ_CODES[1], 
                    "The configuration did not successfully load.").body)
