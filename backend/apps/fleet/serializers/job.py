from django.db.models import Count

from rest_framework import serializers

from core.utils.serializers import ValidatorSerializer
from fleet.actions import ACTIONS, FleetActionInvalidParams, FleetActionUnknown, build_command
from fleet.models import FleetJob, FleetJobTask
from users.serializers.user import SimpleUserSerializer

TASK_STATUSES = tuple(FleetJobTask.STATUS.values)


class FleetJobTaskSerializer(serializers.ModelSerializer):
    node_title = serializers.CharField(source="node.title", read_only=True, default=None)
    is_online = serializers.BooleanField(source="node.is_online", read_only=True, default=None)

    class Meta:
        model = FleetJobTask
        fields = (
            "id",
            "node",
            "node_code",
            "node_title",
            "is_online",
            "status",
            "exit_code",
            "stdout",
            "stderr",
            "error",
            "started_at",
            "finished_at",
        )


class FleetJobSerializer(serializers.ModelSerializer):
    created_by = SimpleUserSerializer(read_only=True)
    tenant_title = serializers.CharField(source="tenant.title", read_only=True)
    action_title = serializers.SerializerMethodField()
    counts = serializers.SerializerMethodField()

    class Meta:
        model = FleetJob
        fields = (
            "id",
            "action",
            "action_title",
            "params",
            "status",
            "counts",
            "tenant",
            "tenant_title",
            "started_at",
            "finished_at",
            "created_at",
            "created_by",
            "updated_at",
        )

    def get_action_title(self, obj) -> str:
        action = ACTIONS.get(obj.action)
        return action.title if action else obj.action

    def get_counts(self, obj) -> dict:
        """
        Reads the annotations from ``FleetJobQuerySet.with_counts`` when they are
        there, and falls back to one query per job when they are not — a wrong
        progress bar is worse than an extra query.
        """
        if hasattr(obj, "task_total"):
            return {"total": obj.task_total, **{status: getattr(obj, f"task_{status}") for status in TASK_STATUSES}}

        counts = dict.fromkeys(TASK_STATUSES, 0)
        for row in obj.tasks.values("status").annotate(count=Count("id")):
            counts[row["status"]] = row["count"]
        return {"total": sum(counts.values()), **counts}


class FleetJobDetailSerializer(FleetJobSerializer):
    tasks = FleetJobTaskSerializer(many=True, read_only=True)

    class Meta(FleetJobSerializer.Meta):
        fields = (*FleetJobSerializer.Meta.fields, "tasks")


class FleetJobCreateSerializer(ValidatorSerializer):
    """
    Validates the request, not the targets: which nodes exist and who may touch
    them is settled in the view, where the tenant scope lives.
    """

    action = serializers.ChoiceField(choices=sorted(ACTIONS))
    params = serializers.DictField(required=False, default=dict)
    node_ids = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=False)
    all_nodes = serializers.BooleanField(default=False)
    tenant = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if bool(attrs.get("node_ids")) == attrs["all_nodes"]:
            raise serializers.ValidationError("Send either `node_ids` or `all_nodes: true` — exactly one.")

        try:
            # Built here so a bad action or bad params is a 400 rather than a job
            # full of failed tasks.
            attrs["command"] = build_command(attrs["action"], attrs.get("params"))
        except FleetActionUnknown as exc:
            raise serializers.ValidationError({"action": str(exc)}) from exc
        except FleetActionInvalidParams as exc:
            raise serializers.ValidationError({"params": str(exc)}) from exc

        return attrs


class FleetJobFilterParams(ValidatorSerializer):
    SORT_FIELDS = (
        "created_at",
        "-created_at",
        "action",
        "-action",
        "status",
        "-status",
    )

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=15)
    status = serializers.ChoiceField(choices=FleetJob.STATUS.values, required=False)
    action = serializers.ChoiceField(choices=sorted(ACTIONS), required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
