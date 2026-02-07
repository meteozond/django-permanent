from django.db.models import Manager


def QuerySetManager(qs):
    """Factory function to create a manager from a QuerySet class."""
    class QuerySetManager(Manager):
        qs_class = qs

        def get_queryset(self):
            return self.qs_class(self.model, using=self._db)

        def get_restore_or_create(self, *args, **kwargs):
            return self.get_queryset().get_restore_or_create(*args, **kwargs)

        def restore(self, *args, **kwargs):
            return self.get_queryset().restore(*args, **kwargs)
    return QuerySetManager()


def MultiPassThroughManager(*classes):
    """
    Create a manager from multiple QuerySet classes
    using multiple inheritance.
    """
    name = "".join([cls.__name__ for cls in classes])
    result_class = type(name, classes, {})
    result = result_class.as_manager()

    globals()[name] = result_class

    return result
