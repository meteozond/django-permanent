from django.db import models, router
from django.db.models.deletion import Collector
from django.utils.module_loading import import_string

from . import settings
from .deletion import *  # NOQA
from .related import *  # NOQA
from .query import NonDeletedQuerySet, DeletedQuerySet, PermanentQuerySet
from .managers import QuerySetManager
from .signals import pre_restore, post_restore


class PermanentModel(models.Model):
    objects = QuerySetManager(NonDeletedQuerySet)
    deleted_objects = QuerySetManager(DeletedQuerySet)
    all_objects = QuerySetManager(PermanentQuerySet)

    class Meta:
        abstract = True
        default_manager_name = 'objects'
        base_manager_name = 'objects'

    class Permanent:
        restore_on_create = False

    def delete(self, using=None, force=False, keep_parents=False):
        using = using or router.db_for_write(self.__class__, instance=self)
        assert self._get_pk_val() is not None, (
            "%s object can't be deleted because its %s attribute is "
            "set to None." % (self._meta.object_name, self._meta.pk.attname)
        )
        collector = Collector(using=using)
        collector.collect([self], keep_parents=keep_parents)
        collector.delete(force=force)

    delete.alters_data = True

    def restore(self):
        pre_restore.send(sender=self.__class__, instance=self)
        setattr(self, settings.FIELD, settings.FIELD_DEFAULT)
        self.save(update_fields=[settings.FIELD])
        post_restore.send(sender=self.__class__, instance=self)


field = import_string(settings.FIELD_CLASS)
PermanentModel.add_to_class(settings.FIELD, field(**settings.FIELD_KWARGS))
