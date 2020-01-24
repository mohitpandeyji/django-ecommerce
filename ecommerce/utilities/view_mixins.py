from typing import Generic, Optional
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from rest_framework.settings import api_settings
from rest_framework.views import APIView

from ecommerce.decorators import overridable
from ecommerce.types import ModelT


class GenericBaseView(APIView, Generic[ModelT]):
    """
    Base view that offers basic view functionality. For extended functionality, mixins should be used.
    To use the get_object* methods, model, queryset or get_queryset must be provided.
    If model is set, queryset will default to model.objects.all()
    If queryset is set, it will override model.
    """
    # Attributes from GenericAPIView
    serializer_class = None
    # If you want to use object lookups other than pk, set 'lookup_field'.
    # For more complex lookup requirements override `get_object()`.
    lookup_field = 'pk'
    lookup_url_kwarg = None
    # The filter backend classes to use for queryset filtering
    filter_backends = api_settings.DEFAULT_FILTER_BACKENDS
    # The style to use for queryset pagination.
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS

    # pylint: disable=pointless-string-statement

    deserializer_class = None

    model: ModelT = None
    """The type of the model to be used in queries. Provides default queryset model.objects.all()"""

    queryset = None
    """The queryset, overrides model."""

    request = None

    permission_classes = [IsAuthenticated]

    requires_authentication = True
    """Whether or not the view requires the user to be authenticated.
    Does not distinguish between different methods.
    Default is True."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._endpoint_handlers = None
        self.request = None
        self._handler = None

    def get_unique_method_identifier(self):
        return id(self.__class__), self.request.method.upper()

    @overridable
    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self,
        }

    @overridable
    def update_permission_classes(self):
        if not self.requires_authentication and IsAuthenticated in self.permission_classes:
            self.permission_classes.remove(IsAuthenticated)

    @overridable
    def invalidate_cache(self):
        self._handler = None
        self.request = None

    @overridable
    def get_endpoint_handlers(self, *_args, **_kwargs):
        if self._endpoint_handlers is None:
            self._endpoint_handlers = {
                getattr(self, func) for func in dir(self)
                if any(name in func for name in self.http_method_names) and hasattr(getattr(self, func),
                                                                                    'endpoint_handler')
            }
        return list(self._endpoint_handlers)

    @overridable
    def get_handler(self):
        if not self._handler:
            candidates = self.get_handler_candidates()
            self._handler = next((func for func in candidates if getattr(func, 'endpoint_handler', False)
                                  and getattr(func, 'method').lower() == self.request.method.lower()),  # noqa: W503
                                 getattr(self, self.request.method.lower(), self.http_method_not_allowed))
        return self._handler

    @overridable
    def get_handler_candidates(self, *_args, **_kwargs):
        return self.get_endpoint_handlers()

    def get_queryset(self):
        if self.queryset is None:
            if self.model:
                return self.model.objects.all()
        return self.queryset

    def process_handler(self, handler, request, *args, **kwargs):
        return handler(request, *args, **kwargs)

    # pylint: disable=attribute-defined-outside-init, broad-except
    # noinspection PyAttributeOutsideInit,PyBroadException
    def dispatch(self, request, *args, **kwargs):
        self.http_request = request
        # Set attributes (as done in the base method)
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers

        try:
            self.initial(self.request, *args, **kwargs)
            handler = self.get_handler()
            self.response = self.process_handler(handler, request, *args, **kwargs)

        except Exception as exc:
            self.response = self.handle_exception(exc)
        try:
            # Can throw another error if serializer selection depends on input. Disregard it.
            self.response = self.finalize_response(request, self.response, *args, **kwargs)
        except Exception:
            pass
        return self.response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Content-Version'] = "1"
        return response

    def filter_queryset(self, queryset):
        """
        Given a queryset, filter it with whichever filter backend is in use.

        You are unlikely to want to override this method, although you may need
        to call it either from a list view, or from a custom `get_object`
        method if you want to apply the configured filtering backend to the
        default queryset.
        """
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    def get_object(self) -> ModelT:
        """
        Returns the object the view is displaying.

        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, ('Expected view %s to be called with a URL keyword argument '
                                                 'named "%s". Fix your URL conf, or set the `.lookup_field` '
                                                 'attribute on the view correctly.' %
                                                 (self.__class__.__name__, lookup_url_kwarg)
                                                 )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    @overridable
    def check_permissions(self, request):
        self.update_permission_classes()
        return super().check_permissions(request)

    @overridable
    def check_object_permissions(self, request, obj):
        return super().check_object_permissions(request, obj)

    def get_object_without_checking_permissions(self, raise_404_on_not_found=False) -> Optional[ModelT]:
        queryset = self.filter_queryset(self.get_queryset())

        if not self.lookup_url_kwarg:
            return None

        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            f"Expected view {self.__class__.__name__} to be called with a URL keyword argument named "
            f"`{lookup_url_kwarg}`. Fix your URL conf, or set the `.lookup_field` attribute on the view correctly.")

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        if raise_404_on_not_found:
            obj = get_object_or_404(queryset, **filter_kwargs)
        else:
            obj = queryset.filter(**filter_kwargs).first()

        return obj

    def get_object_by(self, **kwargs) -> ModelT:
        """
        Helper method to retrieve objects by attributes other than the PK
        :param kwargs: key: value pairs to use in the SQL query
        :return: A filtered QuerySet
        """
        obj = get_object_or_404(self.get_queryset(), **kwargs)
        self.check_object_permissions(self.request, obj)
        return obj

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        if not hasattr(self, '_paginator'):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def get_paginated_response(self, data):
        """
        Return a paginated style `Response` object for the given output data.
        """
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    @staticmethod
    def _find_lte(sorted_list, max_value):
        """Find rightmost value less than or equal to max_value"""
        from bisect import bisect_right
        index = bisect_right(sorted_list, max_value)
        if index:
            return sorted_list[index - 1]
        return None

    @staticmethod
    def get_error_object(key, error_messages):
        return {
            key: error_messages
        }

    # Overridden because CodeFactor does not believe abstract methods are implemented:

    # pylint: disable=useless-super-delegation
    def http_method_not_allowed(self, request, *args, **kwargs):
        return super().http_method_not_allowed(request, *args, **kwargs)

    # pylint: disable=useless-super-delegation
    def get_permissions(self):
        return super().get_permissions()

    # pylint: disable=useless-super-delegation
    def permission_denied(self, request, message=None):
        return super().permission_denied(request, message)
