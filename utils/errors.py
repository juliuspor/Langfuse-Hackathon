from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        self.message = message
        self.details = details


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ExternalServiceError(AppError):
    status_code = 502
    code = "external_service_error"


class ConfigurationError(AppError):
    status_code = 500
    code = "configuration_error"
