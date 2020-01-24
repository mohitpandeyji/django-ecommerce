from typing import List, Union, TypeVar, Type

from django.db import models
from django.db.models import QuerySet as DjangoQuerySet, Manager as DjangoManager

# pylint: disable=invalid-name
T = TypeVar('T')  # Any type.
Queryset = Union[List[T], DjangoQuerySet]
ModelT = TypeVar('ModelT', Type[models.Model], Type[models.Model])
ManagerT = Union[Queryset, DjangoManager]
