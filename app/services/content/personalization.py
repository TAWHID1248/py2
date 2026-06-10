"""Merge field resolution: {first_name}, {company}, etc."""
from app.models.contact import Contact


FIELD_MAP = {
    "first_name": "first_name",
    "last_name": "last_name",
    "company": "company",
    "phone": "phone",
    "email": "email",
    "custom1": "custom1",
    "custom2": "custom2",
    "custom3": "custom3",
    "custom4": "custom4",
    "custom5": "custom5",
}


def build_context(contact: Contact, extra: dict | None = None) -> dict:
    ctx = {
        field: getattr(contact, attr, "") or ""
        for field, attr in FIELD_MAP.items()
    }
    ctx["full_name"] = f"{ctx['first_name']} {ctx['last_name']}".strip()
    if extra:
        ctx.update(extra)
    return ctx


def render(template_str: str, contact: Contact, extra: dict | None = None) -> str:
    """Replace {merge_field} tokens with contact values."""
    ctx = build_context(contact, extra)
    for key, value in ctx.items():
        template_str = template_str.replace(f"{{{key}}}", value)
    return template_str
