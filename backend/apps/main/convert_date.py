def convert_to_timestamp(apps, schema_editor, table_name, field_name):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN temp_{field_name} timestamp with time zone;
        """
        )
        cursor.execute(
            f"""
            UPDATE {table_name}
            SET temp_{field_name} = to_timestamp(
                CASE
                    WHEN {field_name} > 100000000000 THEN {field_name} / 1000.0
                    ELSE {field_name}
                END
            );
        """
        )
        cursor.execute(
            f"""
            ALTER TABLE {table_name}
            DROP COLUMN {field_name};
        """
        )
        cursor.execute(
            f"""
            ALTER TABLE {table_name}
            RENAME COLUMN temp_{field_name} TO {field_name};
        """
        )


def revert_to_bigint(apps, schema_editor, table_name, field_name):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN temp_{field_name} BIGINT;
        """
        )
        cursor.execute(
            f"""
            UPDATE {table_name}
            SET temp_{field_name} = EXTRACT(EPOCH FROM {field_name}::timestamp) * 1000;
        """
        )
        cursor.execute(
            f"""
            ALTER TABLE {table_name}
            DROP COLUMN {field_name};
        """
        )
        cursor.execute(
            f"""
            ALTER TABLE {table_name}
            RENAME COLUMN temp_{field_name} TO {field_name};
        """
        )
