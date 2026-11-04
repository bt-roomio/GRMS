from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permission import check_perms
from main.models import Device, Room
from services.mapping.composite import composite_rule_issues
from services.mapping.constants import Direction
from services.mapping.resolver import TagMapper, Target
from services.mapping.testing import PLAIN, run_composite, run_rule
from services.models import Integration, MappingProfile, MappingRule
from services.serializers.mapping_test import MappingTestSerializer
from services.swagger.mapping_test import mapping_test_swagger
from services.utils.composite_tags import Binding, plan_writes, read_inputs
from services.utils.room_tags import room_input_index


def _scope_of(store: dict, rule) -> str | None:
    """The scope of the profile a mapper took ``rule`` from."""
    return next(((scope for (scope, _), rules in store.items() if any(r is rule for r in rules.values()))), None)


class MappingTestView(APIView):
    """Dry runs of mapping rules: no rule, tag, profile or subscription changes and no RPC."""

    @mapping_test_swagger()
    @check_perms(["services.view_mappingprofile"])
    def post(self, request):
        tenant_id = request.user.tenant_id
        serializer = MappingTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        room, device = self.get_context(tenant_id, params)
        rule, device_id, origin = self.get_rule(tenant_id, params, room, device)

        direction = params["direction"]
        if not params["composite"]:
            report = run_rule(rule, direction, params.get("value"), params.get("tag_ranges"), PLAIN)
            report.update(direction=direction, input=params.get("value"), rule=origin)
            return Response(report)

        index = room_input_index(room, tenant_id) if room is not None else None
        if direction == Direction.TO_EXTERNAL:
            if "inputs" in params:
                report = run_composite(rule, direction, inputs=params["inputs"])
                report.update(input=params["inputs"])
            elif index is None:
                raise ValidationError({"room": ["The device is in no room: give inputs."]})
            elif composite_rule_issues(rule):
                report = run_composite(rule, direction)  # reports the rule's errors
            else:
                inputs = read_inputs(Binding(rule, device_id), index)
                report = run_composite(rule, direction, inputs=inputs.values, unavailable=inputs.unavailable)
                report.update(input=inputs.values, unavailable=inputs.unavailable)
        else:
            plan = None
            if index is not None:

                def plan(composite_rule, value):
                    return plan_writes(Binding(composite_rule, device_id), index, value)

            report = run_composite(rule, direction, value=params["value"], plan=plan)
            report.update(input=params["value"])
        report.update(direction=direction, rule=origin)
        return Response(report)

    @staticmethod
    def get_context(tenant_id, params):
        """The room and device the request names; another tenant's answer 404."""
        if "device" in params:
            devices = Device.objects.filter(tenant_id=tenant_id).select_related("room")
            device = get_object_or_404(devices, pk=params["device"])
            return device.room, device
        if "room" in params:
            return get_object_or_404(Room.objects.by_tenant(tenant_id), pk=params["room"]), None
        return None, None

    def get_rule(self, tenant_id, params, room, device):
        """``(rule, device id its inputs are limited to, where it came from)``."""
        if "rule" in params:
            return params["rule"], None, {"source": "inline"}
        if "composite_rule" in params:
            rule = params["composite_rule"]
            return rule, device.pk if device else None, {"source": "inline"}
        if "profile" in params:
            return self.get_profile_rule(tenant_id, params)
        return self.get_integration_rule(tenant_id, params, room, device)

    @staticmethod
    def get_profile_rule(tenant_id, params):
        profile = get_object_or_404(MappingProfile.objects.by_tenant(tenant_id), pk=params["profile"])
        origin = {"source": "profile", "profile": str(profile.pk), "scope": profile.scope}
        if params["composite"]:
            rule = next((r for r in profile.composite_rules if r.get("id") == params["composite_id"]), None)
            if rule is None:
                raise ValidationError({"composite_id": ["The profile has no composite rule with this id."]})
            return rule, profile.device_id, origin
        row = MappingRule.objects.filter(profile=profile, tag_names__contains=[params["tag_name"]]).first()
        if row is None:
            raise ValidationError({"tag_name": ["The profile has no rule for this tag name."]})
        return row.as_rule(), None, origin

    @staticmethod
    def get_integration_rule(tenant_id, params, room, device):
        integration = get_object_or_404(Integration.objects.filter(tenant_id=tenant_id), pk=params["integration"])
        mapper = TagMapper(integration)
        origin = {"source": "integration", "integration": str(integration.pk)}
        if params["composite"]:
            if device is not None:
                # The device's own profile, its room type's and the tenant's: not its neighbours'.
                bindings = mapper.composites_for_room(room.type_id if room else None, [device.pk])
            elif room is not None:
                bindings = mapper.composites_for_room(room.type_id, room.devices.values_list("id", flat=True))
            else:
                bindings = mapper.composites_for_room(None, [])
            found = next(
                ((rule, device_id) for rule, device_id in bindings if rule["id"] == params["composite_id"]), None
            )
            if found is None:
                raise ValidationError(
                    {"composite_id": ["The integration applies no composite rule with this id here."]}
                )
            return found[0], found[1], {**origin, "scope": _scope_of(mapper.composites, found[0])}
        target = Target(device.pk if device else None, room.type_id if room else None)
        rule = mapper.rule(params["tag_name"], target)
        if rule is None:
            raise ValidationError({"tag_name": ["The integration applies no rule to this tag name here."]})
        return rule, None, {**origin, "scope": _scope_of(mapper.rules, rule)}
