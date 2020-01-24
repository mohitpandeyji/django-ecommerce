from typing import Union

import serpy
from django.db import models
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework import serializers

from ecommerce.types import ModelT, Queryset


class LocalDateTimeField(serpy.Field):
    """A :class: `Field` that converts the value to local datetime using the default timezone."""

    def to_value(self, value):
        return None if not value else timezone.localtime(value)


class DateField(serpy.Field):
    def to_value(self, value):
        return None if not value else serializers.DateField().to_representation(value)


class BaseModelDeserializer(serializers.ModelSerializer):
    pass


class BaseDeserializer(serializers.Serializer):

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class QueryParamValidator(serializers.Serializer):

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class BaseSerializer(serpy.Serializer):
    """
    A serializer that automatically pre-fetches related fields specified in select_related_fields
    and prefetch_related_fields.
    Can also disable serializer fields inherited from a parent serializer using `remove_fields`.
    """

    help_text = None

    select_related_fields = []
    """Related fields that will be selected on instantiation"""

    prefetch_related_fields = []
    """Related fields that will be pre-fetched on instantiation"""

    remove_fields = []
    """Fields that should be removed if this serializer inherits from another serializer"""

    def __init__(self, instance=None, **kwargs):
        super().__init__(instance=instance, **kwargs)
        if self.select_related_fields is None and self.prefetch_related_fields is None:
            raise AttributeError('*_related_fields has not been set')
        self.context = kwargs.get('context')
        self.kwargs = kwargs

    @classmethod
    def setup_eager_loading(cls, instance: Queryset[ModelT], **_kwargs) -> Queryset[ModelT]:
        if isinstance(instance, QuerySet):
            if hasattr(instance, 'select_related') and cls.select_related_fields:
                instance = instance.select_related(*cls.select_related_fields)
            if hasattr(instance, 'prefetch_related') and cls.prefetch_related_fields:
                instance = instance.prefetch_related(*cls.prefetch_related_fields)
        elif hasattr(instance, '__iter__'):
            for item in cls.select_related_fields:
                models.prefetch_related_objects(instance, item)
            for item in cls.prefetch_related_fields:
                models.prefetch_related_objects(instance, item)
        return instance

    def to_value(self, instance: Union[Queryset[ModelT], ModelT]):
        instance = self.setup_eager_loading(instance, **self.kwargs)
        fields = [field for field in self._compiled_fields if field[0] not in self.remove_fields]
        if self.many:
            return [self._serialize(o, fields) for o in instance]

        return self._serialize(instance, fields)


class Timestampable(BaseSerializer):
    created_at = LocalDateTimeField()
    updated_at = LocalDateTimeField()


class SerializerMixinMeta(serpy.serializer.SerializerMeta):
    """
    Meta class for serpy.Serializer mixins
    Also copies select_related, prefetch_related and remove fields to the base classes as required,
    in order to support specifying these fields in the serializer mixin classes.
    """

    # noinspection PyMissingConstructor,PyUnresolvedReferences
    def __init__(cls, what, bases=None, dct=None):
        """
        Extend the attributes of the `BaseSerializer` with the attributes of the SerializerMixin
        :param what:
        :param bases:
              :param dct:
              """
        if not issubclass(cls, BaseSerializer):
            return
        for base in bases:
            if isinstance(base, SerializerMixinMeta):
                cls._update_fields(base, 'select_related_fields')
                cls._update_fields(base, 'prefetch_related_fields')
                cls._update_fields(base, 'remove_fields')

    def _update_fields(cls, base, field):
        existing = getattr(cls, field, [])
        inherited = getattr(base, field, [])
        new = list(existing)
        new.extend(inherited)
        setattr(cls, field, new)


class SerializerMixin(serpy.Serializer, metaclass=SerializerMixinMeta):
    """
    Allows defining a serializer mixin with automatic pre-fetching.
    `select_related_fields`, `prefetch_related_fields` and `remove_fields` fields will be appended to,
     instead of replacing, existing values.
    """
