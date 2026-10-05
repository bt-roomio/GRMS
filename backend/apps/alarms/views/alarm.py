from django.db.models import Count, Q
from django.utils import timezone

from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from alarms.constants import ENTITY_FIELD_WHITELIST
from alarms.models import Alarm, AlarmComment
from alarms.observables.alarm import publish_alarms
from alarms.serializers.alarm import (
    AlarmAssignSerializer,
    AlarmBulkSerializer,
    AlarmCommentCreateSerializer,
    AlarmCommentSerializer,
    AlarmFilterParams,
    AlarmSerializer,
    AlarmSummaryParams,
    AvailableKeysParams,
)
from alarms.services.keys import available_keys
from alarms.services.state import acknowledge_alarm, assign_alarm, clear_alarm
from alarms.swagger.alarm import (
    ack_swagger,
    assign_swagger,
    available_keys_swagger,
    bulk_ack_swagger,
    bulk_clear_swagger,
    clear_swagger,
    comment_create_swagger,
    comment_delete_swagger,
    comment_update_swagger,
    comments_list_swagger,
    delete_swagger,
    list_swagger,
    retrieve_swagger,
    summary_swagger,
    types_swagger,
)
from core.utils.pagination import pagination
from core.utils.permission import check_perms
from fleet.utils.scope import tenant_scope
from users.models import User


def get_alarm(request, pk) -> Alarm:
    return get_object_or_404(Alarm.objects.for_tenant(tenant_scope(request)).with_related(), pk=pk)


class AlarmListView(APIView):
    """The journal and the live list in one place — they differ only by filter."""

    @list_swagger()
    @check_perms(["alarms.view_alarm"])
    def get(self, request):
        params = AlarmFilterParams.check(request.GET)
        queryset = Alarm.objects.list(
            tenant_id=tenant_scope(request),
            types=params.get("alarm_type"),
            severities=params.get("severity"),
            status=params.get("status"),
            device_id=params.get("device"),
            room_id=params.get("room"),
            assignee_id=params.get("assignee"),
            date_from=params.get("date_from"),
            date_to=params.get("date_to"),
            search_value=params.get("search_value"),
            sort_by=params.get("sort_by"),
        )
        serializer = AlarmSerializer(queryset, many=True)
        return Response(pagination(queryset, serializer, params.get("page"), params.get("size")))


class AlarmDetailView(APIView):
    @retrieve_swagger()
    @check_perms(["alarms.view_alarm"])
    def get(self, request, pk):
        return Response(AlarmSerializer(get_alarm(request, pk)).data)

    @delete_swagger()
    @check_perms(["alarms.delete_alarm"])
    def delete(self, request, pk):
        alarm = get_alarm(request, pk)
        tenant_id = alarm.tenant_id
        alarm.delete()
        publish_alarms([tenant_id])
        return Response(status=204)


class AlarmAckView(APIView):
    @ack_swagger()
    @check_perms(["alarms.ack_alarm"])
    def post(self, request, pk):
        alarm = acknowledge_alarm(get_alarm(request, pk), timezone.now(), user=request.user)
        publish_alarms([alarm.tenant_id])
        return Response(AlarmSerializer(alarm).data)


class AlarmClearView(APIView):
    @clear_swagger()
    @check_perms(["alarms.clear_alarm"])
    def post(self, request, pk):
        alarm = get_alarm(request, pk)
        if not alarm.cleared:
            clear_alarm(alarm, timezone.now(), user=request.user, text="Cleared manually")
            publish_alarms([alarm.tenant_id])
        return Response(AlarmSerializer(alarm).data)


class AlarmAssignView(APIView):
    @assign_swagger()
    @check_perms(["alarms.assign_alarm"])
    def post(self, request, pk):
        alarm = get_alarm(request, pk)
        data = AlarmAssignSerializer.check(request.data)

        assignee = None
        if data.get("assignee"):
            assignee = get_object_or_404(User, pk=data["assignee"], tenant_id=alarm.tenant_id, is_active=True)

        assign_alarm(alarm, timezone.now(), assignee=assignee, user=request.user)
        publish_alarms([alarm.tenant_id])
        return Response(AlarmSerializer(alarm).data)


class AlarmCommentView(APIView):
    @comments_list_swagger()
    @check_perms(["alarms.view_alarm"])
    def get(self, request, pk):
        alarm = get_alarm(request, pk)
        comments = AlarmComment.objects.for_alarm(alarm.id)
        return Response(AlarmCommentSerializer(comments, many=True).data)

    @comment_create_swagger()
    @check_perms(["alarms.change_alarm"])
    def post(self, request, pk):
        alarm = get_alarm(request, pk)
        serializer = AlarmCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = AlarmComment.objects.create(
            alarm=alarm,
            user=request.user,
            created_by=request.user,
            alarm_comment_type=AlarmComment.TYPE.OTHER,
            comment={"text": serializer.validated_data["text"]},
        )
        return Response(AlarmCommentSerializer(comment).data, 201)


class AlarmCommentDetailView(APIView):
    """
    Your own comment, editable and removable — the system ones never are.

    A SYSTEM entry is the audit trail of what the evaluator and the operators
    did; letting anyone rewrite it would defeat the point of keeping it.
    """

    @comment_update_swagger()
    @check_perms(["alarms.change_alarm"])
    def put(self, request, pk, comment_pk):
        comment = get_comment(request, pk, comment_pk)
        serializer = AlarmCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment.comment = {
            **(comment.comment or {}),
            "text": serializer.validated_data["text"],
            "edited": True,
            "edited_at": timezone.now().isoformat(),
        }
        comment.save(update_fields=["comment"])
        return Response(AlarmCommentSerializer(comment).data)

    @comment_delete_swagger()
    @check_perms(["alarms.change_alarm"])
    def delete(self, request, pk, comment_pk):
        get_comment(request, pk, comment_pk).delete()
        return Response(status=204)


class AlarmBulkAckView(APIView):
    @bulk_ack_swagger()
    @check_perms(["alarms.ack_alarm"])
    def post(self, request):
        return Response(bulk_apply(request, acknowledge_alarm, Q(acknowledged=False)))


class AlarmBulkClearView(APIView):
    @bulk_clear_swagger()
    @check_perms(["alarms.clear_alarm"])
    def post(self, request):
        return Response(bulk_apply(request, clear_alarm, Q(cleared=False)))


class AlarmSummaryView(APIView):
    """Counters for the dashboard tiles."""

    @summary_swagger()
    @check_perms(["alarms.view_alarm"])
    def get(self, request):
        params = AlarmSummaryParams.check(request.GET)
        queryset = Alarm.objects.list(
            tenant_id=tenant_scope(request),
            status=params.get("status"),
            date_from=params.get("date_from"),
            date_to=params.get("date_to"),
        )

        return Response(
            {
                "total": queryset.count(),
                "active": queryset.filter(cleared=False).count(),
                "unacknowledged": queryset.filter(cleared=False, acknowledged=False).count(),
                "by_severity": count_by(queryset, "severity"),
                "by_type": count_by(queryset, "alarm_type"),
            }
        )


class AlarmTypeView(APIView):
    @types_swagger()
    @check_perms(["alarms.view_alarm"])
    def get(self, request):
        types = (
            Alarm.objects.for_tenant(tenant_scope(request))
            .values_list("alarm_type", flat=True)
            .order_by("alarm_type")
            .distinct()
        )
        return Response({"results": list(types)})


class AvailableKeysView(APIView):
    """
    Telemetry and attribute keys this tenant's devices actually report.

    Without it the rule builder is a blank text field, and a rule with a typo in
    the key silently never fires.
    """

    @available_keys_swagger()
    @check_perms(["main.view_deviceprofile"])
    def get(self, request):
        params = AvailableKeysParams.check(request.GET)
        keys = available_keys(request.user.tenant_id)
        search = (params.get("search_value") or "").lower()

        if search:
            keys = {group: [key for key in values if search in key.lower()] for group, values in keys.items()}

        return Response({**keys, "entity_fields": list(ENTITY_FIELD_WHITELIST)})


def get_comment(request, pk, comment_pk) -> AlarmComment:
    """Only the author's own non-system comment can be reached for writing."""
    alarm = get_alarm(request, pk)
    comment = get_object_or_404(AlarmComment.objects.for_alarm(alarm.id), pk=comment_pk)

    if comment.alarm_comment_type == AlarmComment.TYPE.SYSTEM:
        raise PermissionDenied("System comments are read-only.")
    if comment.user_id != request.user.id:
        raise PermissionDenied("You can only edit your own comments.")

    return comment


def bulk_apply(request, action, pending: Q) -> dict:
    """
    Apply a per-alarm action to a list of ids.

    ``pending`` skips the rows the action would be a no-op on, so the count that
    comes back is what actually changed rather than what was asked for.
    """
    data = AlarmBulkSerializer.check(request.data)
    now = timezone.now()

    alarms = list(Alarm.objects.for_tenant(tenant_scope(request)).filter(pending, id__in=data["ids"]))
    for alarm in alarms:
        action(alarm, now, user=request.user)

    if alarms:
        publish_alarms({alarm.tenant_id for alarm in alarms})

    return {"updated": len(alarms), "requested": len(data["ids"])}


def count_by(queryset, field: str) -> dict:
    return {row[field]: row["total"] for row in queryset.values(field).annotate(total=Count("id")).order_by("-total")}
