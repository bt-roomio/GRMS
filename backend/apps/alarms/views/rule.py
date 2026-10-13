from django.db import transaction

from rest_framework.exceptions import NotFound
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView, Response

from alarms.models import AlarmRule
from alarms.serializers.rule import (
    RULE_FIELDS,
    AlarmRuleBulkSerializer,
    AlarmRuleFilterParams,
    AlarmRulePreviewSerializer,
    AlarmRuleSerializer,
    AlarmRuleTemplateSerializer,
)
from alarms.serializers.rules import validate_profile_alarms
from alarms.services.preview import preview
from alarms.swagger.rule import (
    bulk_swagger,
    create_swagger,
    delete_swagger,
    list_swagger,
    preview_swagger,
    retrieve_swagger,
    templates_swagger,
    update_swagger,
)
from alarms.templates import catalogue
from core.utils.pagination import pagination
from core.utils.permission import check_perms
from fleet.utils.scope import tenant_scope


def get_rule(request, pk) -> AlarmRule:
    return get_object_or_404(AlarmRule.objects.for_tenant(tenant_scope(request)).with_related(), pk=pk)


def get_profile(request, profile):
    """A profile from another tenant is indistinguishable from a missing one."""
    tenant_id = tenant_scope(request)
    if tenant_id is not None and profile.tenant_id != tenant_id:
        raise NotFound("Device profile not found.")
    return profile


def columns(alarm: dict) -> dict:
    """TB rule object → row columns."""
    return {snake: alarm[camel] for camel, snake in RULE_FIELDS if camel in alarm}


class AlarmRuleListView(APIView):
    """
    Rules of a tenant, newest editor first.

    Rules used to live in ``DeviceProfile.profile_data["alarms"]``; they are rows
    now, so editing one no longer means rewriting a whole device profile.
    """

    @list_swagger()
    @check_perms(["alarms.view_alarmrule"])
    def get(self, request):
        params = AlarmRuleFilterParams.check(request.GET)
        queryset = AlarmRule.objects.list(
            tenant_id=tenant_scope(request),
            device_profile=params.get("device_profile"),
            alarm_type=params.get("alarm_type"),
            enabled=params.get("enabled"),
            search_value=params.get("search_value"),
            sort_by=params.get("sort_by"),
        )
        serializer = AlarmRuleSerializer(queryset, many=True)
        return Response(pagination(queryset, serializer, params.get("page"), params.get("size")))

    @create_swagger()
    @check_perms(["alarms.add_alarmrule"])
    def post(self, request):
        serializer = AlarmRuleSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        return Response(serializer.data, 201)


class AlarmRuleDetailView(APIView):
    @retrieve_swagger()
    @check_perms(["alarms.view_alarmrule"])
    def get(self, request, pk):
        return Response(AlarmRuleSerializer(get_rule(request, pk)).data)

    @update_swagger()
    @check_perms(["alarms.change_alarmrule"])
    def put(self, request, pk):
        # Partial on purpose: flipping ``enabled`` should not require resending
        # the whole condition tree.
        serializer = AlarmRuleSerializer(
            get_rule(request, pk),
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    @delete_swagger()
    @check_perms(["alarms.delete_alarmrule"])
    def delete(self, request, pk):
        get_rule(request, pk).delete()
        return Response(status=204)


class AlarmRuleBulkView(APIView):
    """
    Replace every rule of one profile in one call.

    Matching is by ``alarmType``: a rule that stays keeps its row — and therefore
    its id and audit trail — while rules missing from the payload are deleted.
    """

    @bulk_swagger()
    @check_perms(["alarms.change_alarmrule"])
    def post(self, request):
        data = AlarmRuleBulkSerializer.check(request.data)
        profile = get_profile(request, data["device_profile"])
        cleaned = validate_profile_alarms(data["alarms"])

        with transaction.atomic():
            existing = {rule.alarm_type: rule for rule in AlarmRule.objects.filter(device_profile=profile)}
            kept = []

            for alarm in cleaned:
                row = existing.pop(alarm["alarmType"], None)
                values = columns(alarm)

                if row is None:
                    row = AlarmRule.objects.create(
                        tenant_id=profile.tenant_id,
                        device_profile=profile,
                        created_by=request.user,
                        **values,
                    )
                else:
                    for field, value in values.items():
                        setattr(row, field, value)
                    row.updated_by = request.user
                    row.save()

                kept.append(row)

            if existing:
                AlarmRule.objects.filter(id__in=[row.id for row in existing.values()]).delete()

        return Response(AlarmRuleSerializer(kept, many=True).data)


class AlarmRulePreviewView(APIView):
    """
    Dry run before saving — the guard rail against a rule that matches everything.

    Nothing is written: the rules in the body (or the enabled ones already stored)
    are evaluated against the profile's devices as of now.
    """

    @preview_swagger()
    @check_perms(["alarms.view_alarmrule"])
    def post(self, request):
        data = AlarmRulePreviewSerializer.check(request.data)
        profile = get_profile(request, data["device_profile"])

        submitted = data.get("alarms")
        if submitted is None:
            submitted = [rule.as_rule() for rule in AlarmRule.objects.filter(device_profile=profile, enabled=True)]

        return Response(preview(profile.id, validate_profile_alarms(submitted)))


class AlarmRuleTemplateView(APIView):
    """
    The catalogue behind "add a typical rule".

    Templates are not seeded anywhere: a tenant stays without rules until
    somebody picks one. Serving them from here is what keeps the panel, the docs
    and the tests describing the same rules.
    """

    @templates_swagger()
    @check_perms(["alarms.view_alarmrule"])
    def get(self, request):
        return Response({"results": AlarmRuleTemplateSerializer(catalogue(), many=True).data})
