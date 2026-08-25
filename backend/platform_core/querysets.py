from django.core.exceptions import ValidationError
from django.db import models


class AuditEventQuerySet(models.QuerySet):
    """Application-level append-only boundary for audit evidence."""

    def update(self, *args, **kwargs):
        raise ValidationError('audit_events_are_append_only')

    def delete(self, *args, **kwargs):
        raise ValidationError('audit_events_are_append_only')
