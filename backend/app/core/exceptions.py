class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict[str, object] | None = None) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "The requested resource was not found.") -> None:
        super().__init__("NOT_FOUND", message, 404)


class ConflictError(AppError):
    def __init__(self, code: str, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(code, message, 409, details)


class AuthenticationError(AppError):
    def __init__(self, code: str = "AUTHENTICATION_FAILED", message: str = "Invalid credentials.") -> None:
        super().__init__(code, message, 401)


class AuthorizationError(AppError):
    def __init__(self, message: str = "You do not have permission to perform this action.", details: dict[str, object] | None = None) -> None:
        super().__init__("FORBIDDEN", message, 403, details)


class PasswordChangeRequiredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "PASSWORD_CHANGE_REQUIRED",
            "You must change your password before continuing.",
            403,
        )
