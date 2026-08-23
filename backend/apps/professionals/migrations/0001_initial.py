import django.db.models.deletion
import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("portfolios", "0003_portfolio_deleted_at_portfolio_is_deleted")]
    operations = [
        migrations.CreateModel(
            name="Profession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)), ("slug", models.SlugField(max_length=80, unique=True)),
                ("category", models.CharField(blank=True, max_length=100)), ("description", models.TextField(blank=True)),
                ("icon", models.CharField(blank=True, max_length=100)), ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)), ("suggestion_config", models.JSONField(blank=True, default=dict)),
            ], options={"ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="PortfolioProfession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_primary", models.BooleanField(default=False)), ("display_order", models.PositiveIntegerField(default=0)),
                ("portfolio", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="profession_assignments", to="portfolios.portfolio")),
                ("profession", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="portfolio_links", to="professionals.profession")),
            ], options={"ordering": ["display_order", "created_at"]},
        ),
        migrations.AddConstraint(model_name="portfolioprofession", constraint=models.UniqueConstraint(fields=("portfolio", "profession"), name="unique_portfolio_profession")),
        migrations.AddConstraint(model_name="portfolioprofession", constraint=models.UniqueConstraint(condition=models.Q(("is_primary", True)), fields=("portfolio",), name="one_primary_profession")),
    ]
