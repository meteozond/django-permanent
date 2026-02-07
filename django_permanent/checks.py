from django.core import checks
from django.db import models


def _check_permanent_model_relations(app_configs, **kwargs):
    """
    Check that PermanentModel instances don't have CASCADE ForeignKeys
    to non-PermanentModel. This configuration causes IntegrityError
    when the related non-PermanentModel is deleted.
    """
    from .models import PermanentModel

    errors = []

    if app_configs is None:
        from django.apps import apps
        models_to_check = apps.get_models()
    else:
        models_to_check = []
        for app_config in app_configs:
            models_to_check.extend(app_config.get_models())

    for model in models_to_check:
        if not issubclass(model, PermanentModel) or model is PermanentModel:
            continue

        for field in model._meta.get_fields():
            if not isinstance(field, models.ForeignKey):
                continue

            related_model = field.remote_field.model
            on_delete = field.remote_field.on_delete

            if (on_delete == models.CASCADE and
                    not issubclass(related_model, PermanentModel)):
                errors.append(
                    checks.Warning(
                        f'{model.__name__}.{field.name} has CASCADE to '
                        f'non-PermanentModel {related_model.__name__}',
                        hint=(
                            f'PermanentModel with CASCADE ForeignKey to '
                            f'non-PermanentModel may cause IntegrityError '
                            f'when {related_model.__name__} is deleted. '
                            f'Consider: (1) Make {related_model.__name__} '
                            f'a PermanentModel, (2) Use SET_NULL with '
                            f'null=True, or (3) Use DO_NOTHING.'
                        ),
                        obj=model,
                        id='django_permanent.W001',
                    )
                )

    return errors


check_permanent_model_relations = checks.register(checks.Tags.models)(
    _check_permanent_model_relations
)
