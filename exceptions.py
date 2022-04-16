"""Кастомные исключения."""


class APIStatusCodeException(Exception):
    """Исключение для ошибок обращения к эндпоинту."""

    pass


class RequiredTokenIsMissingException(Exception):
    """Исключение для отсутствующих необходимых токенов."""

    pass


class CheckResponseException(Exception):
    """Исключение для неправильного формата ответа в API."""

    pass


class StatusIsUnknownException(Exception):
    """Исключение для неизвестного статуса домашней работы."""

    pass


class SendMessageException(Exception):
    """Исключение для ошибки отправки сообщения."""

    pass


class APIResponseIsIncorrectException(Exception):
    """Исключение для некорректного ответа в API."""

    pass
