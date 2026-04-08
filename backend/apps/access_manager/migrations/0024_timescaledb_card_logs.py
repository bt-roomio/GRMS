from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("access_manager", "0023_guestcard_is_blocked"),
        ("shuttle", "0019_auto_20250706_2338"),  # ensures timescaledb extension is installed
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE access_manager_card_logs_backup AS SELECT * FROM access_manager_card_logs;

            DROP TABLE access_manager_card_logs;

            CREATE TABLE access_manager_card_logs (
                created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                tenant_id       UUID         NOT NULL REFERENCES main_tenant(id) ON DELETE CASCADE,
                number          VARCHAR(200) NOT NULL,
                event_ts        TIMESTAMPTZ  NOT NULL,
                access_group    INTEGER      NOT NULL,
                device_id       UUID         NOT NULL REFERENCES main_device(id),
                staff_id        UUID         REFERENCES access_manager_staff(id),
                guest_id        UUID         REFERENCES main_guest(id),
                additional_info JSONB,
                PRIMARY KEY (event_ts, device_id, number)
            );

            CREATE INDEX ON access_manager_card_logs (tenant_id, event_ts DESC);
            CREATE INDEX ON access_manager_card_logs (device_id, event_ts DESC);
            CREATE INDEX ON access_manager_card_logs (number, event_ts DESC);

            SELECT create_hypertable('access_manager_card_logs', 'event_ts');
            SELECT set_chunk_time_interval('access_manager_card_logs', INTERVAL '1 month');

            INSERT INTO access_manager_card_logs
                (created_at, tenant_id, number, event_ts, access_group, device_id, staff_id, guest_id, additional_info)
            SELECT created_at, tenant_id, number, event_ts, access_group, device_id, staff_id, guest_id, additional_info
            FROM access_manager_card_logs_backup;
            """,
            state_operations=[
                migrations.AlterModelOptions(
                    name="cardlog",
                    options={"managed": False, "ordering": ["-event_ts"]},
                ),
            ],
            reverse_sql="""
            DROP TABLE IF EXISTS access_manager_card_logs;

            ALTER TABLE access_manager_card_logs_backup RENAME TO access_manager_card_logs;
            """,
        ),
    ]
