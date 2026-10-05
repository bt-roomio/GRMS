from django.db import migrations

BATCH_SIZE = 500

RULE_FIELDS = (
    ("createRules", "create_rules"),
    ("clearRule", "clear_rule"),
    ("propagate", "propagate"),
    ("propagateRelationTypes", "propagate_relation_types"),
    ("propagateToOwner", "propagate_to_owner"),
    ("propagateToTenant", "propagate_to_tenant"),
)


def move_rules(apps, schema_editor):
    """
    Lift every rule out of ``DeviceProfile.profile_data["alarms"]`` into a row.

    The old location is cleared in the same pass: nothing reads it any more, so
    a leftover key would be invisible dead configuration that looks live.
    """
    DeviceProfile = apps.get_model("main", "DeviceProfile")
    AlarmRule = apps.get_model("alarms", "AlarmRule")

    rows, touched = [], []

    for profile in DeviceProfile.objects.exclude(profile_data=None).iterator():
        profile_data = profile.profile_data if isinstance(profile.profile_data, dict) else {}
        alarms = profile_data.get("alarms")
        if not isinstance(alarms, list):
            continue

        seen = set()
        for alarm in alarms:
            if not isinstance(alarm, dict):
                continue

            alarm_type = (alarm.get("alarmType") or "").strip()
            # Uniqueness inside a profile used to be the serializer's job and is
            # the table's now; a hand-edited duplicate must not abort the move.
            if not alarm_type or alarm_type in seen:
                continue
            seen.add(alarm_type)

            rows.append(
                AlarmRule(
                    tenant_id=profile.tenant_id,
                    device_profile_id=profile.id,
                    alarm_type=alarm_type,
                    enabled=True,
                    create_rules=alarm.get("createRules") or {},
                    clear_rule=alarm.get("clearRule"),
                    propagate=bool(alarm.get("propagate")),
                    propagate_relation_types=alarm.get("propagateRelationTypes") or [],
                    propagate_to_owner=bool(alarm.get("propagateToOwner")),
                    propagate_to_tenant=bool(alarm.get("propagateToTenant")),
                )
            )

        profile.profile_data = {key: value for key, value in profile_data.items() if key != "alarms"}
        touched.append(profile)

    if rows:
        AlarmRule.objects.bulk_create(rows, batch_size=BATCH_SIZE, ignore_conflicts=True)
    if touched:
        DeviceProfile.objects.bulk_update(touched, ["profile_data"], batch_size=BATCH_SIZE)


def move_rules_back(apps, schema_editor):
    """Put the rules back where ThingsBoard keeps them and drop the rows."""
    DeviceProfile = apps.get_model("main", "DeviceProfile")
    AlarmRule = apps.get_model("alarms", "AlarmRule")

    by_profile: dict = {}
    for rule in AlarmRule.objects.all().iterator():
        alarm = {"id": str(rule.id), "alarmType": rule.alarm_type}
        for camel, snake in RULE_FIELDS:
            alarm[camel] = getattr(rule, snake)
        by_profile.setdefault(rule.device_profile_id, []).append(alarm)

    touched = []
    for profile in DeviceProfile.objects.filter(id__in=list(by_profile)).iterator():
        profile_data = profile.profile_data if isinstance(profile.profile_data, dict) else {}
        profile.profile_data = {**profile_data, "alarms": by_profile[profile.id]}
        touched.append(profile)

    if touched:
        DeviceProfile.objects.bulk_update(touched, ["profile_data"], batch_size=BATCH_SIZE)

    AlarmRule.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("alarms", "0002_alarmrule_alarmrule_uniq_alarm_rule_profile_type"),
        ("main", "0066_alter_tenant_options"),
    ]

    operations = [
        migrations.RunPython(move_rules, move_rules_back),
    ]
