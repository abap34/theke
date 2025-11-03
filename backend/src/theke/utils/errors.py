"""Error handling utilities and decorators."""

import asyncio
import functools
import logging
from typing import Any, Callable, Dict, Optional, Type, TypeVar, cast
from fastapi import HTTPException

from ..types import ServiceError, ValidationError, ExternalAPIError

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


def handle_service_errors(
    default_status_code: int = 500,
    error_mappings: Optional[Dict[Type[Exception], int]] = None
) -> Callable[[F], F]:
    """
    Decorator to handle service errors and convert them to HTTPExceptions.
    
    Args:
        default_status_code: Default status code for unmapped exceptions
        error_mappings: Mapping of exception types to HTTP status codes
    """
    if error_mappings is None:
        error_mappings = {
            ValidationError: 400,
            ValueError: 400,
            FileNotFoundError: 404,
            PermissionError: 403,
            ExternalAPIError: 502,
            ServiceError: 500,
        }
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTPExceptions as-is
                raise
            except Exception as e:
                status_code = error_mappings.get(type(e), default_status_code)
                
                # Log the error with context
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    extra={
                        "function": func.__name__,
                        "exception_type": type(e).__name__,
                        "args": args,
                        "kwargs": kwargs
                    },
                    exc_info=True
                )
                
                # Create appropriate error response
                if isinstance(e, ValidationError):
                    detail = {"message": str(e), "field": getattr(e, 'field', None)}
                elif isinstance(e, ExternalAPIError):
                    detail = {
                        "message": str(e),
                        "service": e.service,
                        "status_code": e.status_code
                    }
                else:
                    detail = {"message": str(e)}
                
                raise HTTPException(status_code=status_code, detail=detail)
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTPExceptions as-is
                raise
            except Exception as e:
                status_code = error_mappings.get(type(e), default_status_code)
                
                # Log the error with context
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    extra={
                        "function": func.__name__,
                        "exception_type": type(e).__name__,
                        "args": args,
                        "kwargs": kwargs
                    },
                    exc_info=True
                )
                
                # Create appropriate error response
                if isinstance(e, ValidationError):
                    detail = {"message": str(e), "field": getattr(e, 'field', None)}
                elif isinstance(e, ExternalAPIError):
                    detail = {
                        "message": str(e),
                        "service": e.service,
                        "status_code": e.status_code
                    }
                else:
                    detail = {"message": str(e)}
                
                raise HTTPException(status_code=status_code, detail=detail)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)
    
    return decorator


def validate_positive_int(value: Any, field_name: str) -> int:
    """Validate that a value is a positive integer."""
    try:
        int_value = int(value)
        if int_value <= 0:
            raise ValidationError(f"{field_name} must be positive", field=field_name)
        return int_value
    except (TypeError, ValueError) as e:
        raise ValidationError(f"{field_name} must be a valid integer", field=field_name) from e


def validate_file_size(file_size: int, max_size: int = 50 * 1024 * 1024) -> None:
    """Validate file size is within limits."""
    if file_size > max_size:
        raise ValidationError(
            f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)",
            field="file_size"
        )


def validate_file_type(filename: str, allowed_types: tuple[str, ...] = ('.pdf',)) -> None:
    """Validate file type by extension."""
    if not any(filename.lower().endswith(ext) for ext in allowed_types):
        raise ValidationError(
            f"File type not allowed. Allowed types: {', '.join(allowed_types)}",
            field="file_type"
        )