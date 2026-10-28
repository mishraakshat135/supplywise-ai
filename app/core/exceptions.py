"""Domain exceptions. main.py maps each one to a proper HTTP status code,
so route code can just `raise NotFoundError(...)`."""


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):  # e.g. duplicate SKU
    status_code = 409


class BusinessRuleError(AppError):  # e.g. negative stock
    status_code = 422


class InvalidStateTransition(AppError):  # e.g. approving an already rejected PO
    status_code = 409
