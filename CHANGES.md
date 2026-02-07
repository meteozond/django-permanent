# CHANGELOG

## 2.0.0 (2026-02-07)

**Related Issues & PRs from MnogoByte/django-permanent:**
- Closes MnogoByte/django-permanent#53 - Cannot restore based on removed date
- Closes MnogoByte/django-permanent#75 - get related object for all_objects
- Closes MnogoByte/django-permanent#78 - Error on django > 3 when django-utils-six is not installed
- Closes MnogoByte/django-permanent#79 - Update deletion.py (same as #78)
- Closes MnogoByte/django-permanent#69 - Installation instructions
- Closes MnogoByte/django-permanent#66 - How is restore_on_create supposed to work?
- Closes MnogoByte/django-permanent#67 - README: Improved description
- Closes MnogoByte/django-permanent#26 - Reorganize generic code (removed 15+ version checks)
- Closes MnogoByte/django-permanent#18 - Implement future imports (not needed for Python 3.10+)

### Breaking Changes

- **Minimum Django version: 4.2 LTS** (supports Django 4.2-5.2, experimental support for Django 6.0, tested with Django 7.0 dev)
- **Minimum Python version: 3.10** (supports 3.10, 3.11, 3.12)
- Dropped Django 1.x, 2.x, 3.x support
- Dropped Python 2.7, 3.4-3.9 support
- Removed django-model-utils dependency

### Improvements

- Modernized codebase for Django 4.2+
- Removed Python 2/six dependencies
- Removed 15+ version compatibility checks
- Simplified QuerySet and Manager implementations
- Updated for Django 5.2 API changes (Collector.delete, ForeignObject.get_extra_restriction, Signal)
- All 44 tests passing with Django 4.2-7.0 dev - 100% pass rate, NO SKIPS! ✅
- Migrated CI/CD from Travis CI to GitHub Actions
- Converted documentation from RST to Markdown (README.md, CHANGES.md)
- Added explicit LICENSE file (BSD)

### CI/CD Enhancements

- Added automated PyPI publishing workflow (GitHub Actions)
  - Automatically publishes to PyPI when version tag is pushed
  - Creates GitHub releases with release notes
  - Auto-updates CHANGES.md with next version template after release
- Improved test infrastructure:
  - Added extras_require for test and dev dependencies (coverage, flake8, coveralls)
  - Added TEST_VERBOSITY environment variable support for flexible test output
  - Improved coverage reporting and Coveralls integration

### New Features

- Added Django System Check (W001) to detect problematic PermanentModel configurations
  - Warns when PermanentModel has CASCADE ForeignKey to non-PermanentModel
  - Helps prevent IntegrityError that occurs when the related non-PermanentModel is deleted
  - Provides helpful suggestions: make related model PermanentModel, use SET_NULL, or use DO_NOTHING

### Async Support

- **Refactored from thread-local variables to contextvars for async-safe operation**
  - All deletion and query context handling now properly supports asyncio
  - `_show_all_permanent` and `_is_deleting` now use `contextvars.ContextVar` instead of thread locals
  - Context managers `deletion_context()` and `show_all_context()` are fully async-safe
  - Prevents race conditions in async environments (ASGI, async views, async ORM operations)
- **Django async ORM support**: Works correctly with Django's async QuerySet API (acount, afirst, aget, etc.)
- **Future-proof**: Ready for Django's continued async expansion in versions 6.0 and 7.0

### Bug Fixes from MnogoByte Fork

- Fixed MnogoByte/django-permanent#53: `restore()` now correctly respects user filters on `removed` field
  - Previously `QuerySet.filter(removed__range=(start, end)).restore()` would restore ALL deleted objects
  - Now only objects matching the filter criteria are restored
  - Improved `_unpatch()` to distinguish automatic patches from user filters
  - Added test case `test_restore_with_date_filter`

- Fixed MnogoByte/django-permanent#75: Access deleted related objects via `show_all_context()`
  - Related objects can now be accessed when soft-deleted using `show_all_context()` context manager
  - Example: `with show_all_context(): obj.foreign_key` now works for deleted related objects
  - Improved `get_queryset_patch()` to respect `show_all_context()` setting
  - Added test case `test_related_object_from_all_objects`

- Fixed MnogoByte/django-permanent#78: Removed `django.utils.six` dependency (already fixed by dropping Python 2)

- Improved documentation (MnogoByte/django-permanent#69, #66, #67):
  - Added Installation section to README with requirements
  - Improved `restore_on_create` documentation with detailed examples
  - Added section on accessing deleted related objects

### Test Changes

- Added test_cascade_to_non_permanent_model_warning to verify system check works correctly
- Removed test_m2m_manager_delete (tested invalid configuration that violates W001 check)
- Removed test_m2m_select_related (obsolete for Django 1.8+, functionality covered by other tests)

### Technical Changes

- **Migrated to contextvars** for async-safe context management (replacing thread-local variables)
- Removed six.iteritems/itervalues usage
- Updated transaction handling (removed commit_on_success_unless_managed)
- Fixed Collector.delete return value for Django 1.9+ behavior
- Updated Signal() to remove deprecated providing_args parameter
- Updated ForeignObject.get_extra_restriction signature for Django 5.2
- Updated QuerySet._update() signature to use *args for Django 4.2-5.2 compatibility (returning_fields parameter)
- Fixed Query.clear_ordering() parameter (force_empty → force)
- Removed ValuesQuerySet/ValuesListQuerySet custom implementations
- Simplified manager system (removed PassThroughManager fallback)
- Added DEFAULT_AUTO_FIELD='django.db.models.BigAutoField' in test configuration for Django 3.2+ compatibility
- Fixed setup.py to reference README.md instead of README.rst

## 1.1.6 (2017-05-04)

- Missing related model all_objects manager bug #65 (thanks @kregoslup)

## 1.1.5 (2017-03-02)

- readme code highlight (thanks @bashu)
- queryset values method bug #62 (thanks @tjacoel)

## 1.1.4 (2016-09-15)

- django 1.10 support #58 (thanks @atin65536)

## 1.1.3 (2016-09-08)

- django 1.9 support #56 (thanks @atin65536)
- values_list support #56 (thanks @atin65536)
- QuerySet pickling bug #55 (thanks @atin65536)

## 1.1.2 (2016-03-30)

- running setup.py without django bug #47

## 1.1.1 (2016-03-16)

- ForeignKey on_delete behaviour bug (thanks @atin65536)

## 1.1.0 (2016-03-16)

- Django 1.9 support
- QuerySetManager support
- Python 3.5 support
- Fixed latest supported model_utls version
- Documentation fixes
- inf recursion on restore_on_create bug
- Python 2.6 support dropped

Thanks to @aidanlister, @atin65536 and @jarekwg, you are awesome!

## 1.0.12 (2015-11-27)

- added pre_restore, post_restore signals thanks atin65536

## 1.0.11 (2015-05-29)

- Fixed deepcopy()-ing PermanentQuerySet #30
- all_objects.select_related bug #31

## 1.0.10 (2015-04-03)

- Skip test_m2m_select_related test on Django 1.8 #27
- Manager isn't available; PermanentModel is abstract #24
- Atomic only for django >= 1.8 #21
- Django 1.8 support
- ReverseSingleRelatedObjectDescriptor patch Bug #25
- Do not try to restore deleted object if it is created already deleted #23

## 1.0.9 (2015-04-02)

- Transaction handling backward compatibility #21
- replaced create_many_related_manager patching with get_extra_restriction patch
- fixed removable m2m through #22

## 1.0.8 (2015-03-27)

- Returned force argument
- Replace commit_on_success_unless_managed by atomic (thanks David Fischer)
- Find packages recursively (thanks David Fischer)
- Make setup.py executable (thanks David Fischer)

## 1.0.7 (2015-03-24)

- Setting trigger field for all removed objects
- Trigger field model save now affects all objects

## 1.0.6 (2015-03-24)

- Fixed PermanentModel.restore() fail
- PermanentModel.delete() now sets removed attribute

## 1.0.5 (2015-03-23)

- Removed fast_deletes fix
- create_many_related_manager patch (For proper m2m)
- Proper Collector patching
- proper Query patching/unpatching
- restore_on_create feature

## 1.0.4 (2015-03-17)

- Many-to-many relations support
- get_restore_or_create bug
- added MIDDLEWARE_CLASSES to reduce Django 1.7 output

## 1.0.3 (2015-03-17)

- Related manager tests
- Double delete tests
- Disabled PermanentModels foreign key updates
- _base_manager override
- Django 1.7 get_restore_or_create bug
- Django 1.7 test structure support
- wrong version in master
- include tests into the package
- Fixed get_restore_or_create hardcoded field name

## 1.0.2 (2014-02-05)

- get_restore_or_create bug
- Trigger field customisation support

## 1.0.1 (2014-02-03)

- Prefetch related bug
- Django 1.6 transactions support
