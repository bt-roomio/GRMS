from functools import partial

from django.db import migrations, models

from main.convert_date import convert_to_timestamp, revert_to_bigint


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("main", "0046_adminsettings_created_by_customer_created_by_and_more"),
    ]

    operations = [
        migrations.RunPython(
            code=partial(convert_to_timestamp, table_name="main_email_configuration", field_name="updated_at"),
            reverse_code=partial(revert_to_bigint, table_name="main_email_configuration", field_name="updated_at"),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="emailconfiguration",
                    name="updated_at",
                    field=models.DateTimeField(auto_now=True, null=True),
                ),
            ],
        ),
        migrations.RunPython(
            code=partial(convert_to_timestamp, table_name="main_email_configuration", field_name="created_at"),
            reverse_code=partial(revert_to_bigint, table_name="main_email_configuration", field_name="created_at"),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="emailconfiguration",
                    name="created_at",
                    field=models.DateTimeField(auto_now_add=True, null=True),
                ),
            ],
        ),
    ]
