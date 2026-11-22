from http import HTTPStatus


class ApplicationError(Exception):
    def __init__(self, message: str, status_code: HTTPStatus):
        self.message = message
        self.status_code = status_code

        super().__init__(message)


class NotFoundException(ApplicationError):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=HTTPStatus.NOT_FOUND)


class ConflictException(ApplicationError):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=HTTPStatus.CONFLICT)


class UnauthorizedException(ApplicationError):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=HTTPStatus.UNAUTHORIZED)


class ForbiddenException(ApplicationError):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=HTTPStatus.FORBIDDEN)


class BadRequestException(ApplicationError):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=HTTPStatus.BAD_REQUEST)
