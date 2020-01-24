from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


class Timestampable(models.Model):
    """
    Adds implementation of the created_at and updated_at datetimes. Uses the timezone specified in the settings.
    Save method is overridden to make sure the updated_at also is in the correct timezone.
    """
    created_at = models.DateTimeField(
        _('created at'),
        default=timezone.now,
        editable=False
    )

    updated_at = models.DateTimeField(
        _('updated at'),
        default=timezone.now
    )

    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.updated_at = timezone.now()
        return super(Timestampable, self).save(force_insert, force_update, using, update_fields)
