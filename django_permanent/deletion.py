# -*- coding: utf-8 -*-
from collections import Counter
from functools import partial, reduce
from operator import attrgetter, or_

from django.db import models, transaction
from django.db.models import signals, sql
from django.db.models.deletion import Collector
from django.utils.timezone import now

from .settings import FIELD
from .related import deletion_context


def delete(self, force=False):
    """
    Patched the BaseCollector.delete with soft delete support
    for PermanentModel
    """
    from .models import PermanentModel
    time = now()

    # sort instance collections
    for model, instances in self.data.items():
        self.data[model] = sorted(instances, key=attrgetter("pk"))

    # if possible, bring the models in an order suitable for databases that
    # don't support transactions or cannot defer constraint checks until the
    # end of a transaction.
    self.sort()
    # number of objects deleted for each model label
    deleted_counter = Counter()

    # Optimize for the case with a single obj and no dependencies
    if len(self.data) == 1:
        model, instances = list(self.data.items())[0]
        if len(instances) == 1:
            instance = instances[0]
            if self.can_fast_delete(instance):
                with transaction.mark_for_rollback_on_error(
                        self.using):
                    if issubclass(model, PermanentModel) and not force:
                        # Soft delete for PermanentModel
                        query = sql.UpdateQuery(model)
                        query.update_batch(
                            [instance.pk], {FIELD: time}, self.using
                        )
                        setattr(instance, FIELD, time)
                        count = 1
                    else:
                        # Hard delete
                        query = sql.DeleteQuery(model)
                        count = query.delete_batch([instance.pk], self.using)
                        setattr(instance, model._meta.pk.attname, None)
                    return count, {model._meta.label: count}

    transaction_handling = partial(
        transaction.atomic, using=self.using, savepoint=False
    )

    # Set context variable to indicate we're in a delete operation
    # This prevents get_extra_restriction from filtering source models
    # during CASCADE (async-safe with contextvars)
    with deletion_context(), transaction_handling():
        # send pre_delete signals
        for model, obj in self.instances_with_model():
            if not model._meta.auto_created:
                signal_kwargs = {
                    'sender': model,
                    'instance': obj,
                    'using': self.using
                }
                if hasattr(self, 'origin'):
                    signal_kwargs['origin'] = self.origin
                signals.pre_delete.send(**signal_kwargs)

        # fast deletes
        for qs in self.fast_deletes:
            # Update PermanentModel instance
            if issubclass(qs.model, PermanentModel) and not force:
                pk_list = [obj.pk for obj in qs]
                qs = sql.UpdateQuery(qs.model)
                qs.update_batch(pk_list, {FIELD: time}, self.using)
                count = len(pk_list)
            else:
                count = qs._raw_delete(using=self.using)

            if count:
                deleted_counter[qs.model._meta.label] += count

        # update fields
        for (field, value), instances_list in self.field_updates.items():
            updates = []
            objs = []
            for instances in instances_list:
                if (isinstance(instances, models.QuerySet) and
                        instances._result_cache is None):
                    updates.append(instances)
                else:
                    objs.extend(instances)

            if updates:
                combined_updates = reduce(or_, updates)
                combined_updates.update(**{field.name: value})
            if objs:
                model = objs[0].__class__
                query = sql.UpdateQuery(model)
                query.update_batch(
                    list({obj.pk for obj in objs}),
                    {field.name: value},
                    self.using
                )

        # reverse instance collections
        for instances in self.data.values():
            instances.reverse()

        # delete instances
        for model, instances in self.data.items():
            pk_list = [obj.pk for obj in instances]
            if issubclass(model, PermanentModel) and not force:
                query = sql.UpdateQuery(model)
                query.update_batch(pk_list, {FIELD: time}, self.using)
                for instance in instances:
                    setattr(instance, FIELD, time)
                count = len(pk_list)
            else:
                query = sql.DeleteQuery(model)
                count = query.delete_batch(pk_list, self.using)

            if count:
                deleted_counter[model._meta.label] += count

            if not model._meta.auto_created:
                for obj in instances:
                    signal_kwargs = {
                        'sender': model,
                        'instance': obj,
                        'using': self.using
                    }
                    if hasattr(self, 'origin'):
                        signal_kwargs['origin'] = self.origin
                    signals.post_delete.send(**signal_kwargs)

        # update collected instances
        for (field, value), objs_list in self.field_updates.items():
            for instances in objs_list:
                for obj in instances:
                    setattr(obj, field.attname, value)
        for model, instances in self.data.items():
            for instance in instances:
                if issubclass(model, PermanentModel) and not force:
                    continue
                setattr(instance, model._meta.pk.attname, None)

        return sum(deleted_counter.values()), dict(deleted_counter)


Collector.delete = delete
