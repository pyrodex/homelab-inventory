"""
Custom exceptions for the application
"""


class HomelabInventoryError(Exception):
    """Base exception for Homelab Inventory"""
    status_code = 500
    message = "An error occurred"

    def __init__(self, message=None, status_code=None):
        super().__init__()
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code

    def to_dict(self):
        return {
            'error': self.__class__.__name__,
            'message': self.message
        }


class ValidationError(HomelabInventoryError):
    """Validation error"""
    status_code = 400
    message = "Validation error"


class NotFoundError(HomelabInventoryError):
    """Resource not found error"""
    status_code = 404
    message = "Resource not found"


class ConflictError(HomelabInventoryError):
    """Conflict error (e.g., duplicate resource)"""
    status_code = 409
    message = "Resource conflict"


class DatabaseError(HomelabInventoryError):
    """Database operation error"""
    status_code = 500
    message = "Database operation failed"


class ReadOnlyDatabaseError(DatabaseError):
    """Database is read-only"""
    status_code = 500
    message = "Database is read-only. Please check file permissions."

