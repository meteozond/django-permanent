import copy
from functools import partial

from django.db.models.deletion import Collector
from django.db.models.query import QuerySet

from django.db.models.query_utils import Q
from django.db.models.sql.where import WhereNode

from . import settings

from .signals import pre_restore, post_restore
from .related import show_all_context


class BasePermanentQuerySet(QuerySet):
    def __deepcopy__(self, memo):
        obj = self.__class__(model=self.model)
        for k, v in self.__dict__.items():
            if k == '_result_cache':
                obj.__dict__[k] = None
            else:
                obj.__dict__[k] = copy.deepcopy(v, memo)
        return obj

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._unpatched = False

    def create(self, **kwargs):
        if not self._unpatched:
            if (self.model.Permanent.restore_on_create and
                    not kwargs.get(settings.FIELD)):
                qs = self.get_unpatched()
                return qs.get_restore_or_create(**kwargs)
        return super().create(**kwargs)

    def get_restore_or_create(self, **kwargs):
        qs = self.get_unpatched()
        obj, created = qs.get_or_create(**kwargs)
        if isinstance(obj, dict):
            geter, seter = obj.get, obj.__setitem__
        else:
            geter, seter = partial(getattr, obj), partial(setattr, obj)

        if not created and geter(settings.FIELD, True):
            pre_restore.send(sender=self.model, instance=obj)
            seter(settings.FIELD, settings.FIELD_DEFAULT)
            self.model.all_objects.filter(id=geter('id')).update(
                **{settings.FIELD: settings.FIELD_DEFAULT}
            )
            post_restore.send(sender=self.model, instance=obj)

        return obj

    def delete(self, force=False):
        """Delete the records in the current QuerySet."""
        if self.query.is_sliced:
            raise TypeError("Cannot use 'limit' or 'offset' with delete().")
        if (hasattr(self.query, 'distinct_fields') and
                self.query.distinct_fields):
            raise TypeError("Cannot call delete() after .distinct(*fields).")
        if hasattr(self, '_fields') and self._fields is not None:
            raise TypeError(
                "Cannot call delete() after .values() or .values_list()"
            )

        del_query = self._chain()

        # The delete is actually 2 queries - one to find related objects,
        # and one to delete. Make sure that the discovery of related
        # objects is performed on the same database as the deletion.
        del_query._for_write = True

        # Disable non-supported fields.
        del_query.query.select_for_update = False
        del_query.query.select_related = False
        del_query.query.clear_ordering(force=True)

        collector = Collector(using=del_query.db, origin=self)
        collector.collect(del_query)
        deleted, _rows_count = collector.delete(force=force)

        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None

        return deleted, _rows_count

    delete.alters_data = True

    def restore(self):
        return self.get_unpatched().update(
            **{settings.FIELD: settings.FIELD_DEFAULT}
        )

    def _update(self, values, *args, **kwargs):
        # Modifying trigger field has to affect all objects
        field_names = [field.attname for field, _, _ in values]
        if (settings.FIELD in field_names and
                not getattr(self, '_unpatched', False)):
            return self.get_unpatched()._update(values, *args, **kwargs)
        return super()._update(values, *args, **kwargs)

    def get_unpatched(self):
        qs = self._clone()
        qs._unpatch()
        return qs

    def _clone(self, *args, **kwargs):
        c = super()._clone(*args, **kwargs)
        # We need clones stay unpatched
        if getattr(self, '_unpatched', False):
            c._unpatched = True
            c._unpatch()
        return c

    def _patch(self, q_object):
        self.query.add_q(q_object)

    def _unpatch(self):
        self._unpatched = True
        if not self.query.where.children:
            return

        # Remove only the automatic patch added in __init__,
        # not user filters. Automatic patches are always the first
        # condition and match specific lookups
        condition = self.query.where.children[0]

        # Check if this is an automatic patch:
        # - NonDeletedQuerySet adds: Q(removed=None)
        #   -> 'isnull' lookup or 'exact' with None
        # - DeletedQuerySet adds: ~Q(removed=None)
        #   -> negated 'isnull' or NOT with None
        is_auto_patch = False
        if (hasattr(condition, 'lhs') and
                condition.lhs.target.name == settings.FIELD):
            # Check if it's a simple isnull or exact lookup
            # (not range, gte, etc.)
            lookup_name = getattr(condition, 'lookup_name', None)
            if lookup_name in ('isnull', 'exact'):
                is_auto_patch = True

        if is_auto_patch:
            del self.query.where.children[0]


class NonDeletedQuerySet(BasePermanentQuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.query.where:
            self._patch(Q(**{settings.FIELD: settings.FIELD_DEFAULT}))


class DeletedWhereNode(WhereNode):
    pass


class DeletedQuerySet(BasePermanentQuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.query.where:
            self.query.where_class = DeletedWhereNode
            self._patch(~Q(**{settings.FIELD: settings.FIELD_DEFAULT}))


class AllWhereNode(WhereNode):
    pass


class PermanentQuerySet(BasePermanentQuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.query.where:
            self.query.where_class = AllWhereNode

    def _fetch_all(self):
        # Set context variable before fetching to indicate all objects
        # should be shown (async-safe with contextvars)
        with show_all_context():
            return super()._fetch_all()
