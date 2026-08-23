import django.core.validators
import django.db.models.deletion
import uuid

from django.db import migrations, models


BASE = [
    ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
    ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
    ("is_deleted", models.BooleanField(default=False)), ("deleted_at", models.DateTimeField(blank=True, null=True)),
    ("sort_order", models.PositiveIntegerField(default=0)), ("is_visible", models.BooleanField(default=True)),
    ("version", models.PositiveIntegerField(default=1)),
    ("portfolio", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_set", to="portfolios.portfolio")),
]


class Migration(migrations.Migration):
    initial = True
    dependencies = [("portfolios", "0003_portfolio_deleted_at_portfolio_is_deleted")]
    operations = [
        migrations.CreateModel(name="Experience", fields=BASE + [("title", models.CharField(max_length=200)), ("organization", models.CharField(max_length=200)), ("employment_type", models.CharField(blank=True, max_length=50)), ("location", models.CharField(blank=True, max_length=200)), ("start_date", models.DateField()), ("end_date", models.DateField(blank=True, null=True)), ("is_current", models.BooleanField(default=False)), ("description_html", models.TextField(blank=True)), ("description_editor_json", models.JSONField(blank=True, default=dict)), ("highlights", models.JSONField(blank=True, default=list))], options={"ordering": ["sort_order", "-start_date"]}),
        migrations.CreateModel(name="Education", fields=BASE + [("institution", models.CharField(max_length=200)), ("degree", models.CharField(blank=True, max_length=200)), ("field_of_study", models.CharField(blank=True, max_length=200)), ("start_date", models.DateField(blank=True, null=True)), ("end_date", models.DateField(blank=True, null=True)), ("grade", models.CharField(blank=True, max_length=100)), ("description_html", models.TextField(blank=True)), ("description_editor_json", models.JSONField(blank=True, default=dict))], options={"ordering": ["sort_order", "-end_date"]}),
        migrations.CreateModel(name="Skill", fields=BASE + [("name", models.CharField(max_length=120)), ("category", models.CharField(blank=True, max_length=100)), ("proficiency", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])), ("years_experience", models.PositiveSmallIntegerField(blank=True, null=True))], options={"ordering": ["sort_order", "name"]}),
        migrations.CreateModel(name="Certification", fields=BASE + [("name", models.CharField(max_length=200)), ("issuer", models.CharField(max_length=200)), ("issue_date", models.DateField(blank=True, null=True)), ("expiry_date", models.DateField(blank=True, null=True)), ("credential_id", models.CharField(blank=True, max_length=200)), ("credential_url", models.URLField(blank=True))], options={"ordering": ["sort_order", "-issue_date"]}),
        migrations.CreateModel(name="Achievement", fields=BASE + [("title", models.CharField(max_length=200)), ("issuer", models.CharField(blank=True, max_length=200)), ("date", models.DateField(blank=True, null=True)), ("description_html", models.TextField(blank=True)), ("description_editor_json", models.JSONField(blank=True, default=dict))], options={"ordering": ["sort_order", "-date"]}),
    ]
