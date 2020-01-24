import logging

from functools import wraps

from rest_framework.exceptions import PermissionDenied

LOGGER = logging.getLogger(__name__)


def overridable(arg=None):
    """
    This method can be overridden by other classes in the inheritance tree. Direct inheritance is not required. When
    this method is called, this decorator will look for an identically named method decorated with 'overrides' in the
    inheritance tree and call that method instead. If no overriding method is found, this method is called.
    """

    def decorator(func):
        setattr(func, 'overridable', True)
        setattr(func, 'handler_cache', dict())

        @wraps(func)
        def wrapper(instance, *args, **kwargs):
            # Get the method resolution order
            mro = instance.__class__.__mro__
            # Make a combined key from the classes in the hierarchy tree (these can affect which candidate is selected)
            # and the name of the function
            cache_key = hash(mro + (func.__name__,))
            handler = func.handler_cache.get(cache_key, None)

            if not handler:
                # Get identically named functions
                candidates = {getattr(cls, func.__name__) for cls in mro if hasattr(cls, func.__name__)}
                # Of these functions, get the ones decorated with 'overrides'. Doing this in two steps saves unnecessary
                # getattr calls. Sort by priority.
                handlers = sorted({f for f in candidates if hasattr(f, 'overrides')},
                                  key=lambda x: getattr(x, 'priority', 1), reverse=True)

                if len(handlers) >= 2:
                    # Found more than one suitable handler. Get the two first for comparison.
                    first_handler = handlers[0]
                    second_handler = handlers[1]
                    if getattr(first_handler, 'priority', 1) == getattr(second_handler, 'priority', 1):
                        # The two first handlers have the same priority; cannot pick one.
                        raise AttributeError(f"Cannot find a more specific overriding method: "
                                             f"{first_handler.__str__()} or {second_handler.__str__()}. Use the "
                                             f"'priority' param.")

                handler = handlers[0] if handlers else func
                # Cache handler
                func.handler_cache[cache_key] = handler

            # Return the highest prioritized overriding function or the overridable function if none were found
            return handler(instance, *args, **kwargs)

        return wrapper

    return decorator(arg) if callable(arg) else decorator


def access_permissions(permission):
    """
    django-rest-framework permission decorator for custom methods.
    Ex:- @access_permissions('saml.view_samlconfiguration')
    """

    def decorator(drf_custom_method):
        def _decorator(self, args, *kwargs):
            user_permission = permission
            if self.request.user.has_perm(user_permission):
                return drf_custom_method(self, args, *kwargs)
            else:
                raise PermissionDenied()

        return _decorator

    return decorator
