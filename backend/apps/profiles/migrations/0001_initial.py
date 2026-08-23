import django.db.models.deletion
import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("portfolios", "0003_portfolio_deleted_at_portfolio_is_deleted")]
    operations = [migrations.CreateModel(name="Profile", fields=[
        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
        ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
        ("full_name", models.CharField(blank=True, max_length=200)), ("headline", models.CharField(blank=True, max_length=250)),
        ("biography_html", models.TextField(blank=True)), ("biography_editor_json", models.JSONField(blank=True, default=dict)),
        ("avatar_id", models.UUIDField(blank=True, null=True)), ("email", models.EmailField(blank=True, max_length=254)),
        ("phone", models.CharField(blank=True, max_length=50)), ("city", models.CharField(blank=True, max_length=100)),
        ("country", models.CharField(blank=True, max_length=100)), ("timezone", models.CharField(blank=True, max_length=64)),
        ("social_links", models.JSONField(blank=True, default=list)), ("available_for_work", models.BooleanField(default=False)),
        ("open_to_relocation", models.BooleanField(default=False)), ("version", models.PositiveIntegerField(default=1)),
        ("portfolio", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to="portfolios.portfolio")),
    ])]
