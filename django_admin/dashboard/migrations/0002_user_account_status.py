from django.db import migrations, models


class Migration(migrations.Migration):
    """Keep Django's unmanaged-model state aligned with FastAPI's schema."""

    dependencies = [("dashboard", "0001_initial")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="user",
                    name="is_active",
                    field=models.BooleanField(default=True),
                ),
                migrations.AlterField(
                    model_name="user",
                    name="role",
                    field=models.CharField(
                        choices=[
                            ("ADMIN", "admin"),
                            ("STAFF", "staff"),
                            ("CUSTOMER", "customer"),
                        ],
                        max_length=20,
                    ),
                ),
            ],
        )
    ]
