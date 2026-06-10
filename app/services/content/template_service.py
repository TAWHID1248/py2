"""Jinja2 template rendering with merge field + spintax support."""
from jinja2 import Environment, BaseLoader, Undefined
from app.models.contact import Contact
from app.models.template import Template
from app.services.content.personalization import build_context
from app.services.content.spinner_service import spin


class SilentUndefined(Undefined):
    def __str__(self):
        return f"{{{self._undefined_name}}}"


_env = Environment(loader=BaseLoader(), undefined=SilentUndefined, autoescape=False)


class TemplateService:
    def render(
        self,
        template: Template,
        contact: Contact,
        use_spintax: bool = False,
        use_synonyms: bool = False,
        extra: dict | None = None,
    ) -> tuple[str, str | None, str | None]:
        """Return (subject, html_body, text_body) fully personalized."""
        ctx = build_context(contact, extra)

        subject = self._render_str(template.subject, ctx)
        html = self._render_str(template.html_body or "", ctx)
        text = self._render_str(template.text_body or "", ctx)

        if use_spintax:
            seed = contact.id
            subject = spin(subject, use_synonyms, seed)
            html = spin(html, use_synonyms, seed)
            text = spin(text, use_synonyms, seed)

        return subject, html or None, text or None

    def _render_str(self, src: str, ctx: dict) -> str:
        try:
            tmpl = _env.from_string(src)
            return tmpl.render(**ctx)
        except Exception:
            return src
