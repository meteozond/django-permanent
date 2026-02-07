# Django Permanent

Yet another approach to provide soft (logical) delete or masking (thrashing) django models instead of deleting them physically from db.

[![Tests](https://github.com/meteozond/django-permanent/actions/workflows/test.yml/badge.svg)](https://github.com/meteozond/django-permanent/actions/workflows/test.yml)

## Installation

Install using pip:

```bash
pip install django-permanent
```

Or install from source:

```bash
git clone https://github.com/meteozond/django-permanent.git
cd django-permanent
python setup.py install
```

**Requirements:**
- Python 3.10+
- Django 4.2+

## Quick Start

To create a non-deletable model just inherit it from `PermanentModel`:

```python
class MyModel(PermanentModel):
    pass
```

It automatically changes delete behaviour to hide objects instead of deleting them:

```python
>>> a = MyModel.objects.create(pk=1)
>>> b = MyModel.objects.create(pk=2)
>>> MyModel.objects.count()
2
>>> a.delete()
>>> MyModel.objects.count()
1
```

To recover a deleted object just call its `restore` method:

```python
>>> a.restore()
>>> MyModel.objects.count()
2
```

Use the `force` kwarg to enforce physical deletion:

```python
>>> a.delete(force=True) # Will act as the default django delete
>>> MyModel._base_manager.count()
0
```

### Restore on Create

If you want `create()` to restore deleted objects instead of raising an integrity error on unique constraints, use the `restore_on_create` option:

```python
class Article(PermanentModel):
    title = models.CharField(max_length=100, unique=True)

    class Permanent:
        restore_on_create = True
```

**How it works:**

When `restore_on_create = True`, calling `Model.objects.create(**kwargs)` will:
1. First try to find a matching object (including soft-deleted ones)
2. If found and deleted: restore it and update with new kwargs
3. If found and not deleted: return the existing object
4. If not found: create a new object

**Example:**

```python
>>> article = Article.objects.create(title="Django Tips")
>>> article.delete()  # Soft delete
>>> Article.objects.count()
0

# Without restore_on_create: would raise IntegrityError
# With restore_on_create: restores the deleted article
>>> article2 = Article.objects.create(title="Django Tips")
>>> article2.pk == article.pk  # Same object!
True
>>> Article.objects.count()
1
```

**Note:** This feature is most useful for models with unique constraints where you want to "resurrect" deleted objects rather than creating duplicates.

## Managers

It changes the default model manager to ignore deleted objects, adding a `deleted_objects` manager to see them instead:

```python
>>> MyModel.objects.count()
2
>>> a.delete()
>>> MyModel.objects.count()
1
>>> MyModel.deleted_objects.count()
1
>>> MyModel.all_objects.count()
2
>>> MyModel._base_manager.count()
2
```

### Accessing Deleted Related Objects

By default, accessing a foreign key to a deleted object will raise `DoesNotExist`. Use `show_all_context()` to access deleted related objects:

```python
from django_permanent.related import show_all_context

# Create models with relationship
parent = ParentModel.objects.create(name="parent")
child = ChildModel.objects.create(parent=parent)

# Soft delete parent
parent.delete()

# Without show_all_context: raises DoesNotExist
child.parent  # Raises ParentModel.DoesNotExist

# With show_all_context: can access deleted parent
with show_all_context():
    print(child.parent.name)  # Works! Returns "parent"
```

**Note:** This is useful when you need to access relationships to soft-deleted objects, for example in admin interfaces or audit logs.

## QuerySet

The `QuerySet.delete` method will act as the default django delete, with one exception - objects of models subclassing `PermanentModel` will be marked as deleted; the rest will be deleted physically:

```python
>>> MyModel.objects.all().delete()
```

You can still force django query set physical deletion:

```python
>>> MyModel.objects.all().delete(force=True)
```

## Using custom querysets

1. Inherit your query set from `PermanentQuerySet`:

   ```python
   class ServerFileQuerySet(PermanentQuerySet)
       pass
   ```

2. Wrap `PermanentQuerySet` or `DeletedQuerySet` in you model manager declaration:

   ```python
   class MyModel(PermanentModel)
       objects = MultiPassThroughManager(ServerFileQuerySet, NonDeletedQuerySet)
       deleted_objects = MultiPassThroughManager(ServerFileQuerySet, DeletedQuerySet)
       all_objects = MultiPassThroughManager(ServerFileQuerySet, PermanentQuerySet)
   ```

## Method `get_restore_or_create`

1. Check for existence of the object.
2. Restore it if it was deleted.
3. Create a new one, if it was never created.

## Field name

The default field named is 'removed', but you can override it with the PERMANENT_FIELD variable in settings.py:

```python
PERMANENT_FIELD = 'deleted'
```

## Requirements

- Django 4.2+
- Python 3.10, 3.11, 3.12+

## Testing

The project uses GitHub Actions for continuous integration.

**Run tests locally using act (GitHub Actions locally):**

```bash
# Install act (macOS)
brew install act

# Run all tests in parallel
act

# Run specific Python version
act --matrix python-version:3.11

# Run specific Python/Django combination
act --matrix python-version:3.11 --matrix django-version:"Django>=4.2,<5.0"
```

**Run tests directly:**

```bash
# Install dependencies
pip install "Django>=4.2,<5.0" coverage flake8

# Run linter
flake8 django_permanent

# Run tests with coverage
coverage run runtests.py
coverage report
```
