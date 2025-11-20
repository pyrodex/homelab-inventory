"""
Standardized API response utilities
"""
from flask import jsonify
from typing import Any, Optional, Dict


def success_response(data: Any = None, message: str = None, status_code: int = 200) -> tuple:
    """
    Create a standardized success response
    
    Args:
        data: Response data (dict, list, or object)
        message: Optional success message
        status_code: HTTP status code (default: 200)
    
    Returns:
        Tuple of (response, status_code)
    """
    response = {
        'success': True,
        'data': data,
    }
    
    if message:
        response['message'] = message
    
    return jsonify(response), status_code


def error_response(
    message: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 400,
    error_code: Optional[str] = None
) -> tuple:
    """
    Create a standardized error response
    
    Args:
        message: Error message
        details: Optional error details (e.g., validation errors)
        status_code: HTTP status code (default: 400)
        error_code: Optional error code for programmatic handling
    
    Returns:
        Tuple of (response, status_code)
    """
    response = {
        'success': False,
        'error': message,
    }
    
    if details:
        response['details'] = details
    
    if error_code:
        response['error_code'] = error_code
    
    return jsonify(response), status_code


def validation_error_response(validation_errors: Dict[str, Any], message: str = "Validation error") -> tuple:
    """
    Create a standardized validation error response
    
    Args:
        validation_errors: Dictionary of field errors from Marshmallow
        message: Error message
    
    Returns:
        Tuple of (response, status_code)
    """
    return error_response(
        message=message,
        details=validation_errors,
        status_code=400,
        error_code='VALIDATION_ERROR'
    )


def not_found_response(resource: str = "Resource", resource_id: Any = None) -> tuple:
    """
    Create a standardized not found response
    
    Args:
        resource: Resource type name
        resource_id: Optional resource ID
    
    Returns:
        Tuple of (response, status_code)
    """
    message = f"{resource} not found"
    if resource_id is not None:
        message += f" (ID: {resource_id})"
    
    return error_response(
        message=message,
        status_code=404,
        error_code='NOT_FOUND'
    )


def conflict_response(message: str = "Resource already exists") -> tuple:
    """
    Create a standardized conflict response
    
    Args:
        message: Error message
    
    Returns:
        Tuple of (response, status_code)
    """
    return error_response(
        message=message,
        status_code=409,
        error_code='CONFLICT'
    )


def rate_limit_response(message: str = "Rate limit exceeded") -> tuple:
    """
    Create a standardized rate limit response
    
    Args:
        message: Error message
    
    Returns:
        Tuple of (response, status_code)
    """
    return error_response(
        message=message,
        status_code=429,
        error_code='RATE_LIMIT_EXCEEDED'
    )


def server_error_response(message: str = "Internal server error") -> tuple:
    """
    Create a standardized server error response
    
    Args:
        message: Error message
    
    Returns:
        Tuple of (response, status_code)
    """
    return error_response(
        message=message,
        status_code=500,
        error_code='INTERNAL_ERROR'
    )

