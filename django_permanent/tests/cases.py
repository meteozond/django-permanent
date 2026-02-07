from django_permanent.signals import post_restore, pre_restore

from django.db import models
from django.db.models.signals import post_delete
from django.test import TestCase
from django.utils.timezone import now

from django_permanent.tests.test_app.models import (
    RegularModel, RemovableRegularDepended
)
from .test_app.models import (
    CustomQsPermanent,
    LazyReferencePermanent,
    M2MFrom,
    M2MTo,
    MyPermanentModel,
    MyPermanentModelWithManager,
    NonRemovableDepended,
    NonRemovableNullableDepended,
    RemovableNullableDepended,
    PermanentDepended,
    PermanentM2MThrough,
    RemovableDepended,
    RestoreOnCreateModel,
)


class TestDelete(TestCase):
    def setUp(self):
        self.permanent = MyPermanentModel.objects.create()

    def test_deletion(self):
        model = MyPermanentModel
        permanent2 = model.objects.create()
        self.permanent.delete()
        self.assertTrue(self.permanent.removed)
        self.assertEqual(list(model.objects.all()), [permanent2])
        self.assertEqual(
            list(model.all_objects.all()), [self.permanent, permanent2]
        )
        self.assertEqual(list(model.deleted_objects.all()), [self.permanent])

    def test_depended(self):
        model = RemovableDepended
        model.objects.create(dependence=self.permanent)
        self.permanent.delete()
        self.assertEqual(list(model.objects.all()), [])

    def test_non_removable_depended(self):
        model = NonRemovableDepended
        depended = model.objects.create(dependence=self.permanent)
        self.permanent.delete()
        self.assertEqual(list(model.objects.all()), [depended])

    def test_non_removable_nullable_depended(self):
        model = NonRemovableNullableDepended
        model.objects.create(dependence=self.permanent)
        self.permanent.delete()
        depended = model.objects.first()
        self.assertEqual(depended.dependence, None)

    def test_removable_nullable_depended(self):
        model = RemovableNullableDepended
        model.objects.create(dependence=self.permanent)
        self.permanent.delete()
        depended = model.objects.first()
        self.assertEqual(depended.dependence, None)

    def test_remove_removable_nullable_depended(self):
        model = RemovableRegularDepended
        regular = RegularModel.objects.create(name='Test')
        test_model = model.objects.create(dependence=regular)
        test_model.delete()
        try:
            self.assertIsNotNone(model.deleted_objects.first().dependence)
        except AttributeError:
            self.fail()

    def test_permanent_depended(self):
        model = PermanentDepended
        depended = model.objects.create(dependence=self.permanent)
        self.permanent.delete()
        self.assertEqual(list(model.objects.all()), [])
        self.assertEqual(list(model.deleted_objects.all()), [depended])
        new_depended = model.all_objects.get(pk=depended.pk)
        new_permanent = MyPermanentModel.all_objects.get(pk=self.permanent.pk)
        self.assertTrue(new_depended.removed)
        self.assertTrue(new_permanent.removed)
        self.assertEqual(new_depended.dependence_id, self.permanent.id)

    def test_related(self):
        p = PermanentDepended.objects.create(dependence=self.permanent)
        self.permanent.delete()
        result = list(
            PermanentDepended.all_objects.select_related('dependence').all()
        )
        self.assertEqual(result, [p])

    def test_double_delete(self):
        self.called = 0

        def post_delete_receiver(*args, **kwargs):
            self.called += 1

        post_delete.connect(post_delete_receiver, sender=PermanentDepended)

        model = PermanentDepended
        model.objects.create(dependence=self.permanent, removed=now())
        model.objects.create(dependence=self.permanent)
        self.permanent.delete()
        self.assertEqual(self.called, 1)

    def test_restore(self):
        self.called_pre = 0
        self.called_post = 0

        def pre_restore_receiver(sender, instance, **kwargs):
            self.called_pre += 1

        def post_restore_receiver(sender, instance, **kwargs):
            self.called_post += 1

        pre_restore.connect(pre_restore_receiver)
        post_restore.connect(post_restore_receiver)

        self.permanent.delete()
        self.permanent.restore()
        self.assertFalse(self.permanent.removed)
        self.assertEqual(
            list(MyPermanentModel.objects.all()), [self.permanent]
        )

        pre_restore.disconnect(pre_restore_receiver)
        post_restore.disconnect(post_restore_receiver)

        self.assertEqual(self.called_pre, 1)
        self.assertEqual(self.called_post, 1)

    def test_forced_model_delete(self):
        self.permanent.delete(force=True)
        self.assertEqual(MyPermanentModel.all_objects.count(), 0)

    def test_forced_queryset_delete(self):
        MyPermanentModel.objects.all().delete(force=True)
        self.assertEqual(MyPermanentModel.all_objects.count(), 0)

    def test_forced_model_delete_removed(self):
        self.permanent.delete()
        self.permanent.delete(force=True)
        self.assertEqual(MyPermanentModel.all_objects.count(), 0)

    def test_forced_querset_delete_removed(self):
        self.permanent.delete()
        MyPermanentModel.all_objects.all().delete(force=True)
        self.assertEqual(MyPermanentModel.all_objects.count(), 0)


class TestIntegration(TestCase):
    def test_prefetch_bug(self):
        permanent1 = MyPermanentModel.objects.create()
        NonRemovableDepended.objects.create(dependence=permanent1)
        MyPermanentModel.objects.prefetch_related(
            'nonremovabledepended_set'
        ).all()
        NonRemovableDepended.all_objects.prefetch_related('dependence').all()

    def test_related_manager_bug(self):
        permanent = MyPermanentModel.objects.create()
        PermanentDepended.objects.create(dependence=permanent)
        PermanentDepended.objects.create(
            dependence=permanent, removed=now()
        )
        self.assertEqual(permanent.permanentdepended_set.count(), 1)
        self.assertEqual(PermanentDepended.objects.count(), 1)

    def test_m2m_manager(self):
        _from = M2MFrom.objects.create()
        _to = M2MTo.objects.create()
        PermanentM2MThrough.objects.create(
            m2m_from=_from, m2m_to=_to, removed=now()
        )
        self.assertEqual(_from.m2mto_set.count(), 0)

    def test_m2m_manager_clear(self):
        _from = M2MFrom.objects.create()
        _to = M2MTo.objects.create()
        PermanentM2MThrough.objects.create(m2m_from=_from, m2m_to=_to)
        self.assertEqual(_from.m2mto_set.count(), 1)
        _from.m2mto_set.clear()
        self.assertEqual(_from.m2mto_set.count(), 0)
        self.assertEqual(PermanentM2MThrough.objects.count(), 0)
        self.assertEqual(PermanentM2MThrough.all_objects.count(), 1)
        self.assertEqual(M2MFrom.objects.count(), 1)
        self.assertEqual(M2MTo.objects.count(), 1)

    def test_m2m_prefetch_related(self):
        _from = M2MFrom.objects.create()
        _to = M2MTo.objects.create()
        PermanentM2MThrough.objects.create(m2m_from=_from, m2m_to=_to)
        PermanentM2MThrough.objects.create(
            m2m_from=_from, m2m_to=_to, removed=now()
        )
        m2mto_set = M2MFrom.objects.prefetch_related(
            'm2mto_set'
        ).get(pk=_from.pk).m2mto_set
        self.assertSequenceEqual(m2mto_set.all(), [_to])
        self.assertEqual(m2mto_set.count(), 1)

    def test_m2m_all_objects(self):
        dependence = MyPermanentModel.objects.create(removed=now())
        depended = NonRemovableDepended.objects.create(
            dependence=dependence, removed=now()
        )
        depended = NonRemovableDepended.all_objects.get(pk=depended.pk)
        self.assertEqual(depended.dependence, dependence)

    def test_m2m_deleted_through(self):
        _from = M2MFrom.objects.create()
        _to = M2MTo.objects.create()
        PermanentM2MThrough.objects.create(
            m2m_from=_from, m2m_to=_to, removed=now()
        )
        self.assertEqual(M2MFrom.objects.filter(m2mto__id=_to.pk).count(), 0)


class TestPassThroughManager(TestCase):
    def test_pass_through_manager(self):
        self.assertTrue(hasattr(CustomQsPermanent.objects, 'test'))
        self.assertTrue(hasattr(CustomQsPermanent.objects, 'restore'))
        self.assertTrue(CustomQsPermanent.objects.get_restore_or_create(id=10))


class TestCustomQSMethods(TestCase):
    def test__get_restore_or_create__get(self):
        self.obj = MyPermanentModel.objects.create(name="old")
        result = MyPermanentModel.objects.get_restore_or_create(name="old")
        self.assertEqual(result.id, 1)

    def test__get_restore_or_create__restore(self):
        self.called_pre = 0
        self.called_post = 0

        def pre_restore_receiver(sender, instance, **kwargs):
            self.called_pre += 1

        def post_restore_receiver(sender, instance, **kwargs):
            self.called_post += 1

        pre_restore.connect(pre_restore_receiver)
        post_restore.connect(post_restore_receiver)

        obj = MyPermanentModel.objects.create(name="old", removed=now())
        result = MyPermanentModel.objects.get_restore_or_create(name="old")
        self.assertEqual(result.id, obj.id)
        self.assertEqual(MyPermanentModel.objects.count(), 1)
        self.assertEqual(MyPermanentModel.all_objects.count(), 1)

        pre_restore.disconnect(pre_restore_receiver)
        post_restore.disconnect(post_restore_receiver)

        self.assertEqual(self.called_pre, 1)
        self.assertEqual(self.called_post, 1)

    def test__get_restore_or_create__create(self):
        MyPermanentModel.objects.get_restore_or_create(name="old")
        result = MyPermanentModel.objects.get_restore_or_create(name="old")
        self.assertEqual(result.id, 1)
        self.assertEqual(MyPermanentModel.objects.count(), 1)
        self.assertEqual(MyPermanentModel.all_objects.count(), 1)

    def test_restore(self):
        MyPermanentModel.objects.create(name="old", removed=now())
        MyPermanentModel.objects.filter(name="old").restore()
        self.assertEqual(MyPermanentModel.objects.count(), 1)
        self.assertEqual(MyPermanentModel.all_objects.count(), 1)

    def test_restore_on_create(self):
        MyPermanentModel.Permanent.restore_on_create = True
        first = MyPermanentModel.objects.create(
            name='unique', removed=now()
        )
        second = MyPermanentModel.objects.create(name='unique')
        self.assertEqual(first, second)
        MyPermanentModel.Permanent.restore_on_create = False

    def test_restore_with_date_filter(self):
        """
        Test that restore() respects user filters on removed field
        (Issue #53)
        """
        from datetime import timedelta

        # Create objects removed at different times
        old_time = now() - timedelta(days=10)
        recent_time = now() - timedelta(days=1)

        obj1 = MyPermanentModel.objects.create(
            name="old", removed=old_time
        )
        obj2 = MyPermanentModel.objects.create(
            name="recent", removed=recent_time
        )
        obj3 = MyPermanentModel.objects.create(
            name="very_recent", removed=now()
        )

        # Restore only objects removed in the last 5 days
        cutoff = now() - timedelta(days=5)
        MyPermanentModel.deleted_objects.filter(removed__gte=cutoff).restore()

        # Check that only recent objects were restored
        self.assertEqual(MyPermanentModel.objects.count(), 2)
        self.assertEqual(MyPermanentModel.deleted_objects.count(), 1)

        # Verify the old one is still deleted
        obj1_fresh = MyPermanentModel.all_objects.get(pk=obj1.pk)
        self.assertIsNotNone(obj1_fresh.removed)

        # Verify recent ones are restored
        obj2_fresh = MyPermanentModel.all_objects.get(pk=obj2.pk)
        obj3_fresh = MyPermanentModel.all_objects.get(pk=obj3.pk)
        self.assertIsNone(obj2_fresh.removed)
        self.assertIsNone(obj3_fresh.removed)

    def test_related_object_from_all_objects(self):
        """Test accessing deleted related objects (Issue #75)"""
        from django_permanent.tests.test_app.models import NonRemovableDepended
        from django_permanent.related import show_all_context

        # Create target and object that references it
        target = MyPermanentModel.objects.create(name="target")
        dependent = NonRemovableDepended.objects.create(dependence=target)

        # Soft delete the target
        target.delete()

        # Verify target is deleted
        self.assertEqual(MyPermanentModel.objects.count(), 0)
        self.assertEqual(MyPermanentModel.deleted_objects.count(), 1)

        # Get dependent (not deleted)
        dependent_fresh = NonRemovableDepended.objects.get(pk=dependent.pk)

        # Without show_all_context: raises DoesNotExist
        with self.assertRaises(MyPermanentModel.DoesNotExist):
            _ = dependent_fresh.dependence

        # With show_all_context: can access deleted related object
        with show_all_context():
            related_target = dependent_fresh.dependence
            self.assertIsNotNone(related_target)
            self.assertEqual(related_target.name, "target")
            self.assertIsNotNone(related_target.removed)


class TestCustomManager(TestCase):
    def setUp(self):
        MyPermanentModelWithManager.objects.create(name="regular")
        MyPermanentModelWithManager.objects.create(
            name="removed", removed=now()
        )

    def test_custom_method(self):
        MyPermanentModelWithManager.objects.test()

    def test_non_removed(self):
        self.assertEqual(MyPermanentModelWithManager.objects.count(), 1)

    def test_removed(self):
        self.assertEqual(MyPermanentModelWithManager.objects.count(), 1)

    def test_all(self):
        self.assertEqual(MyPermanentModelWithManager.any_objects.count(), 2)


class RetoreOnCreateTestCase(TestCase):
    def setUp(self):
        self.obj = RestoreOnCreateModel.objects.create(name='obj1')

    def test_restore_on_create(self):
        self.obj.delete()
        new_obj = RestoreOnCreateModel.objects.create(name='obj1')

        self.assertEqual(new_obj.pk, self.obj.pk)


class SystemCheckTestCase(TestCase):
    def test_cascade_to_non_permanent_model_warning(self):
        """
        Test that system check warns about CASCADE FK
        to non-PermanentModel.
        """
        from django.db import models
        from django_permanent.models import PermanentModel
        from django_permanent.checks import _check_permanent_model_relations

        class TestRegularModel(models.Model):
            class Meta:
                app_label = 'test_check'

        class TestBadPermanent(PermanentModel):
            regular = models.ForeignKey(
                TestRegularModel, on_delete=models.CASCADE
            )

            class Meta:
                app_label = 'test_check'

        class MockAppConfig:
            def get_models(self):
                return [TestBadPermanent]

        warnings = _check_permanent_model_relations(
            app_configs=[MockAppConfig()]
        )

        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].id, 'django_permanent.W001')
        self.assertIn('CASCADE', warnings[0].msg)
        self.assertIn('TestBadPermanent', warnings[0].msg)
        self.assertIn('TestRegularModel', warnings[0].msg)

    def test_warning_contains_required_information(self):
        from django_permanent.checks import _check_permanent_model_relations

        warnings = _check_permanent_model_relations(app_configs=None)

        for warning in warnings:
            self.assertEqual(warning.id, 'django_permanent.W001')
            self.assertIn('CASCADE', warning.msg)
            self.assertIn('PermanentModel', warning.hint)
            self.assertIn('IntegrityError', warning.hint)
            self.assertIn('SET_NULL', warning.hint)

    def test_correct_configurations_no_warnings(self):
        from django_permanent.checks import _check_permanent_model_relations

        class MockAppConfig:
            def get_models(self):
                return [
                    NonRemovableDepended,
                    NonRemovableNullableDepended,
                    PermanentDepended,
                ]

        warnings = _check_permanent_model_relations(
            app_configs=[MockAppConfig()]
        )

        self.assertEqual(len(warnings), 0)

    def test_lazy_reference_resolved(self):
        """
        Test that lazy references (strings) are resolved by Django.
        LazyReferencePermanent uses string refs instead of classes.
        """
        # VERIFY: Django resolved lazy references to actual classes
        permanent_field = LazyReferencePermanent._meta.get_field('permanent')
        regular_field = LazyReferencePermanent._meta.get_field('regular')

        self.assertIsInstance(permanent_field, models.ForeignKey)
        self.assertIsInstance(regular_field, models.ForeignKey)

        # remote_field.model should be CLASS, not string!
        self.assertIs(permanent_field.remote_field.model, MyPermanentModel)
        self.assertIs(regular_field.remote_field.model, RegularModel)

        # Both should be actual types, not strings
        self.assertIsInstance(permanent_field.remote_field.model, type)
        self.assertIsInstance(regular_field.remote_field.model, type)


class AsyncDeletionTestCase(TestCase):
    """Test async deletion via Django ORM async API."""

    async def test_async_soft_delete_object(self):
        """Test async soft delete of a single object."""
        from .test_app.models import MyPermanentModel

        # Create object asynchronously
        obj = await MyPermanentModel.objects.acreate(name="test")
        obj_id = obj.pk

        # Soft delete asynchronously
        await obj.adelete()

        # Object should not be visible in default manager
        count = await MyPermanentModel.objects.acount()
        self.assertEqual(count, 0)

        # Object should be in deleted_objects
        deleted_count = await MyPermanentModel.deleted_objects.acount()
        self.assertEqual(deleted_count, 1)

        # Object should be in all_objects
        all_count = await MyPermanentModel.all_objects.acount()
        self.assertEqual(all_count, 1)

        # Verify the object is marked as removed
        deleted_obj = await MyPermanentModel.all_objects.aget(pk=obj_id)
        self.assertIsNotNone(deleted_obj.removed)

    async def test_async_soft_delete_queryset(self):
        """Test async soft delete via queryset."""
        from .test_app.models import MyPermanentModel

        # Create multiple objects
        await MyPermanentModel.objects.acreate(name="test1")
        await MyPermanentModel.objects.acreate(name="test2")
        await MyPermanentModel.objects.acreate(name="test3")

        # Delete via queryset
        deleted, _ = await MyPermanentModel.objects.filter(
            name__startswith="test"
        ).adelete()

        self.assertEqual(deleted, 3)

        # All should be soft deleted
        count = await MyPermanentModel.objects.acount()
        self.assertEqual(count, 0)

        deleted_count = await MyPermanentModel.deleted_objects.acount()
        self.assertEqual(deleted_count, 3)

    async def test_async_restore(self):
        """Test async restore of deleted objects."""
        from .test_app.models import MyPermanentModel
        from asgiref.sync import sync_to_async

        # Create and delete
        obj = await MyPermanentModel.objects.acreate(name="test")
        obj_id = obj.pk
        await obj.adelete()

        # Verify deleted
        count = await MyPermanentModel.objects.acount()
        self.assertEqual(count, 0)

        # Restore using sync_to_async (restore() is sync)
        deleted_obj = await MyPermanentModel.deleted_objects.aget(pk=obj_id)
        await sync_to_async(deleted_obj.restore)()

        # Verify restored
        count = await MyPermanentModel.objects.acount()
        self.assertEqual(count, 1)

        deleted_count = await MyPermanentModel.deleted_objects.acount()
        self.assertEqual(deleted_count, 0)

    async def test_async_force_delete(self):
        """Test async force delete (permanent deletion)."""
        from .test_app.models import MyPermanentModel
        from asgiref.sync import sync_to_async

        # Create object
        obj = await MyPermanentModel.objects.acreate(name="test")

        # Force delete (adelete doesn't support custom params)
        # Use sync_to_async wrapper
        await sync_to_async(obj.delete)(force=True)

        # Should be completely gone
        count = await MyPermanentModel.objects.acount()
        self.assertEqual(count, 0)

        deleted_count = await MyPermanentModel.deleted_objects.acount()
        self.assertEqual(deleted_count, 0)

        all_count = await MyPermanentModel.all_objects.acount()
        self.assertEqual(all_count, 0)

    async def test_async_cascade_delete(self):
        """Test async cascade deletion with ForeignKey."""
        from .test_app.models import MyPermanentModel, PermanentDepended

        # Create parent and child
        parent = await MyPermanentModel.objects.acreate(name="parent")
        await PermanentDepended.objects.acreate(dependence=parent)

        # Delete parent - should cascade to child
        await parent.adelete()

        # Both should be soft deleted
        parent_count = await MyPermanentModel.objects.acount()
        self.assertEqual(parent_count, 0)

        child_count = await PermanentDepended.objects.acount()
        self.assertEqual(child_count, 0)

        # Both should be in deleted_objects
        deleted_parents = await MyPermanentModel.deleted_objects.acount()
        self.assertEqual(deleted_parents, 1)

        deleted_children = await PermanentDepended.deleted_objects.acount()
        self.assertEqual(deleted_children, 1)

    async def test_async_concurrent_deletions(self):
        """Test concurrent async deletions are properly isolated."""
        import asyncio
        from .test_app.models import MyPermanentModel

        # Create objects
        obj1 = await MyPermanentModel.objects.acreate(name="obj1")
        obj2 = await MyPermanentModel.objects.acreate(name="obj2")
        obj3 = await MyPermanentModel.objects.acreate(name="obj3")

        # Delete concurrently
        await asyncio.gather(
            obj1.adelete(),
            obj2.adelete(),
            obj3.adelete()
        )

        # All should be deleted
        count = await MyPermanentModel.objects.acount()
        self.assertEqual(count, 0)

        deleted_count = await MyPermanentModel.deleted_objects.acount()
        self.assertEqual(deleted_count, 3)
