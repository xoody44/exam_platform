from fastapi import HTTPException


def bad_request(detail: str) -> HTTPException:
    """400 - некорректный запрос."""
    return HTTPException(status_code=400, detail=detail)


def unauthorized(detail: str = "Требуется авторизация") -> HTTPException:
    """401 - нет токена или токен невалиден."""
    return HTTPException(status_code=401, detail=detail)


def forbidden(detail: str = "Доступ запрещён") -> HTTPException:
    """403 - токен есть, но прав не хватает."""
    return HTTPException(status_code=403, detail=detail)


def not_found(detail: str = "Не найдено") -> HTTPException:
    """404 - сущность не найдена."""
    return HTTPException(status_code=404, detail=detail)


def conflict(detail: str) -> HTTPException:
    """409 - конфликт состояния, например повторное завершение попытки."""
    return HTTPException(status_code=409, detail=detail)
