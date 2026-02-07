import contextvars
from contextlib import contextmanager

from django.db.models.fields.related import ForeignObject
from django.db.models.expressions import Col
from django.db.models.sql.where import WhereNode
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor as Descriptor
)

from . import settings


# Context variables for tracking query context (async-safe)
_show_all_permanent = contextvars.ContextVar(
    'show_all_permanent',
    default=False
)
_is_deleting = contextvars.ContextVar('is_deleting', default=False)


@contextmanager
def deletion_context():
    """Context manager for deletion operations (async-safe)."""
    token = _is_deleting.set(True)
    try:
        yield
    finally:
        _is_deleting.reset(token)


@contextmanager
def show_all_context():
    """
        Context manager for showing all objects including deleted (async-safe).
    """
    token = _show_all_permanent.set(True)
    try:
        yield
    finally:
        _show_all_permanent.reset(token)


def get_extra_restriction_patch(func):
    def wrapper(self, alias, related_alias):
        cond = func(self, alias, related_alias)

        from .models import PermanentModel

        # In Django 5.2+, get_extra_restriction is called with
        # (alias, related_alias) where alias is the table being joined TO
        # (target of ForeignKey) and related_alias is the table containing
        # the ForeignKey

        # Check if we're in an all_objects context - don't filter if so
        if _show_all_permanent.get():
            return cond

        if cond is None:
            cond = WhereNode()

        # Case 1: Filter the target model if it's PermanentModel
        # (e.g., when joining from PermanentDepended to MyPermanentModel)
        target_model = self.remote_field.model
        if issubclass(target_model, PermanentModel):
            try:
                field = target_model._meta.get_field(settings.FIELD)
                if settings.FIELD_DEFAULT is None:
                    lookup = field.get_lookup('isnull')(
                        Col(alias, field, field), True
                    )
                else:
                    lookup = field.get_lookup('exact')(
                        Col(alias, field, field), settings.FIELD_DEFAULT
                    )
                cond.add(lookup, 'AND')
            except Exception:
                pass

        # Case 2: Also filter the source model if it's PermanentModel
        # (e.g., when joining through PermanentM2MThrough)
        # NOTE: We ONLY do this for SELECT queries, NOT for DELETE/CASCADE
        # operations to avoid IntegrityError during CASCADE deletion
        if not _is_deleting.get():
            source_model = self.model
            if (issubclass(source_model, PermanentModel) and
                    source_model != target_model):
                try:
                    field = source_model._meta.get_field(settings.FIELD)
                    if settings.FIELD_DEFAULT is None:
                        lookup = field.get_lookup('isnull')(
                            Col(related_alias, field, field), True
                        )
                    else:
                        lookup = field.get_lookup('exact')(
                            Col(related_alias, field, field),
                            settings.FIELD_DEFAULT
                        )
                    cond.add(lookup, 'AND')
                except Exception:
                    pass

        return cond
    return wrapper


ForeignObject.get_extra_restriction = get_extra_restriction_patch(
    ForeignObject.get_extra_restriction
)


def get_queryset_patch(func):
    def wrapper(self, **hints):
        from .models import PermanentModel
        instance = hints.get('instance')
        model = self.field.remote_field.model

        # If we're in show_all_context, use all_objects to include deleted
        if _show_all_permanent.get():
            if hasattr(model, 'all_objects'):
                return model.all_objects
            return model.objects

        # If the instance itself is deleted, use all_objects
        if (instance and isinstance(instance, PermanentModel) and
                getattr(instance, settings.FIELD)):
            if hasattr(model, 'all_objects'):
                return model.all_objects
            return model.objects

        return func(self, **hints)
    return wrapper


Descriptor.get_queryset = get_queryset_patch(Descriptor.get_queryset)
