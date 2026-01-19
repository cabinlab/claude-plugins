"""
UI command handlers for triggering Fusion 360 dialogs
"""
import adsk.core
import adsk.fusion
from handlers.base import BaseHandler
from core.errors import ValidationError, FusionAPIError


class TriggerUICommandHandler(BaseHandler):
    """Handler for trigger_ui_command action

    Triggers Fusion 360 UI commands/dialogs by command ID.
    This enables semi-automated workflows where the agent prepares geometry
    and then triggers the appropriate dialog for user completion.

    Common use cases:
    - Triggering "Convert to Sheet Metal" dialog after preparing geometry
    - Opening the Bend tool with prepared bend lines
    - Triggering flat pattern creation
    """

    # Known command IDs with descriptions for error messages
    KNOWN_COMMANDS = {
        # Sheet Metal commands (research needed for exact IDs)
        # "SheetMetalConvertCmd": "Convert to Sheet Metal",
        # "SheetMetalBendCmd": "Create Bend",
        # "SheetMetalFlatPatternCmd": "Create Flat Pattern",
    }

    def validate(self, args: dict) -> dict:
        """Validate trigger UI command arguments"""
        self.validators.validate_required_fields(args, ["command_id"])

        command_id = self.validators.validate_non_empty_string(args["command_id"], "command_id")
        message = args.get("message", "")

        return {
            "command_id": command_id,
            "message": message
        }

    def execute(self, args: dict) -> dict:
        """Execute trigger UI command action"""
        app = adsk.core.Application.get()
        ui = app.userInterface

        command_id = args["command_id"]

        # Get the command definition
        cmd_def = ui.commandDefinitions.itemById(command_id)

        if not cmd_def:
            # List available command categories for debugging
            available_hint = "Command ID not found. Use Fusion 360's Text Commands (Shift+S) to discover command IDs."
            raise ValidationError(f"Unknown command ID: '{command_id}'. {available_hint}")

        # Execute the command (this opens the dialog)
        try:
            cmd_def.execute()
        except Exception as e:
            raise FusionAPIError(f"Failed to execute command '{command_id}': {str(e)}")

        result = {
            "triggered": True,
            "command_id": command_id
        }

        # Include guidance message if provided
        if args.get("message"):
            result["guidance"] = args["message"]

        return result
