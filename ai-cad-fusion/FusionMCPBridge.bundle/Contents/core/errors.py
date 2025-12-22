"""
Error classes matching existing bridge error codes
"""


class BridgeError(Exception):
    """Base error class with structured error codes"""
    
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"{code}: {message}")


class ValidationError(BridgeError):
    """Input validation errors -> E_BAD_ARGS"""
    def __init__(self, message: str, field: str = None):
        details = {"field": field} if field else {}
        super().__init__("E_BAD_ARGS", message, details)


class FusionAPIError(BridgeError):
    """Fusion API operation errors -> E_RUNTIME"""
    def __init__(self, message: str, operation: str = None):
        details = {"operation": operation} if operation else {}
        super().__init__("E_RUNTIME", message, details)


class ActionNotSupportedError(BridgeError):
    """Unknown action -> E_ACTION_UNSUPPORTED"""
    def __init__(self, action: str):
        super().__init__("E_ACTION_UNSUPPORTED", f"Unknown action: {action}")
