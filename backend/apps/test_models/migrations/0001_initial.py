# ruff: noqa: E501, I001
import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("portfolios", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScopedRecord",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("name", models.CharField(max_length=100)),
                (
                    "portfolio",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="scopedrecord_set",
                        to="portfolios.portfolio",
                    ),
                ),
            ],
            options={
                "base_manager_name": "all_objects",
                "default_manager_name": "objects",
                "indexes": [
                    models.Index(
                        fields=["portfolio", "-created_at"],
                        name="test_models_sc_portfol_4e2a44_idx",
                    )
                ],
            },
        ),
    ]
