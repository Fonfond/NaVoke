import re


class InvalidPhoneError(ValueError):
    """Телефон не приводится к формату 7XXXXXXXXXX."""


def normalize_phone(value: str) -> str:
    """Оставляет цифры и приводит номер к виду 79991234567."""
    digits = re.sub(r'\D', '', value or '')

    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    elif len(digits) == 10:
        digits = '7' + digits

    if len(digits) != 11 or not digits.startswith('7'):
        raise InvalidPhoneError('Телефон должен быть в формате +7XXXXXXXXXX')

    return digits


def try_normalize_phone(value: str):
    """Вернуть нормализованный телефон или None для не-телефонных username."""
    try:
        return normalize_phone(value)
    except InvalidPhoneError:
        return None
