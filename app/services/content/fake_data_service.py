"""Faker integration for sender name randomization."""
try:
    from faker import Faker as _Faker
    _faker = _Faker()
except ImportError:
    _faker = None


def random_name() -> str:
    if _faker:
        return _faker.name()
    return "Marketing Team"


def random_first_name() -> str:
    if _faker:
        return _faker.first_name()
    return "Team"


def random_company() -> str:
    if _faker:
        return _faker.company()
    return "Company"
