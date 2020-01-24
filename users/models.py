import uuid
from datetime import timedelta

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from model_utils.fields import StatusField

from ecommerce.utilities.model_mixins import Timestampable
from users.managers import UserManager


class User(PermissionsMixin, AbstractBaseUser, Timestampable):
    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'
    # For the createsuperuser command only.
    REQUIRED_FIELDS = ['email']

    objects = UserManager()

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True
    )

    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True)

    first_name = models.CharField(
        _('first name'),
        max_length=255)

    last_name = models.CharField(
        _('last name'),
        max_length=255)

    # This field is for better searching.
    full_name = models.CharField(
        _('full name'),
        max_length=255,
        blank=True
    )

    email = models.EmailField(
        _('email address'), unique=True)

    date_of_birth = models.DateField(
        _('date of birth'),
        blank=True, null=True
    )

    date_joined = models.DateTimeField(
        _('date joined'),
        blank=True, null=True
    )

    # SETTINGS

    is_staff = models.BooleanField(
        _('is staff'),
        default=False
    )

    # deleted AND invited users will have is_active false
    is_active = models.BooleanField(
        _('is active'),
        default=False
    )

    STATUS_INVITED = 'invited'
    STATUS_ACCEPTED = 'accepted'

    # invalidate complete user registration emails if activation_status is accepted
    ACTIVATION_STATUS = Choices(
        STATUS_INVITED,
        STATUS_ACCEPTED

    )

    activation_status = StatusField(
        verbose_name="Activation status",
        choices_name='ACTIVATION_STATUS'
    )

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.full_name} – {self.username}"

    # pylint: disable=arguments-differ
    def save(self, *args, **kwargs):
        self.full_name = self.get_full_name()
        super().save(*args, **kwargs)

    def get_full_name(self):
        return '{} {}'.format(self.first_name, self.last_name) if self.first_name and self.last_name else ''


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    token = models.CharField(max_length=255, unique=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.id:
            self.token = get_random_string(length=50)
        super(PasswordResetToken, self).save(
            force_insert, force_update, using, update_fields
        )

    def is_expired(self):
        delta = timezone.now() - self.created_at
        return delta > timedelta(hours=48)
