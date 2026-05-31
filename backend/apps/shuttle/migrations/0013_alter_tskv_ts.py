from django.db import migrations, models
from django.utils import timezone

class Migration(migrations.Migration):

    dependencies = [
        ('shuttle', '0012_alter_attributekv_last_update_ts_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE shuttle_ts_kv "
                "ALTER COLUMN ts TYPE timestamp with time zone "
                "USING to_timestamp(ts / 1000.0)"
            ),
            reverse_sql=(
                "ALTER TABLE shuttle_ts_kv "
                "ALTER COLUMN ts TYPE bigint "
                "USING (extract(epoch from ts) * 1000)::bigint"
            )
        ),
        migrations.AlterField(
            model_name='tskv',
            name='ts',
            field=models.DateTimeField(default=timezone.now),
        ),
    ]
