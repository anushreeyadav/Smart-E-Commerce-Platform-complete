from django.db import migrations, models


class Migration(migrations.Migration):
    """Django state only; FastAPI Alembic owns the shared products schema."""

    dependencies = [("dashboard", "0002_user_account_status")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="product",
                    name="category",
                    field=models.CharField(max_length=100),
                ),
                migrations.AddField(
                    model_name="product",
                    name="popularity",
                    field=models.IntegerField(default=0),
                ),
                migrations.AddField(
                    model_name="product",
                    name="is_active",
                    field=models.BooleanField(default=True),
                ),
            ],
        )
    ]
