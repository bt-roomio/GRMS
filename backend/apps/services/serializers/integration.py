from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from core.utils.serializers import ValidatorSerializer
from services.models import Integration, Integrator, MappingOverride, MappingProfile
from services.serializers.mapping import override_errors


class IntegrationSerializer(serializers.ModelSerializer):
    integrator = serializers.SlugRelatedField(slug_field="name", queryset=Integrator.objects.all())
    mapping_profile = serializers.PrimaryKeyRelatedField(
        queryset=MappingProfile.objects.none(),
        required=False,
        allow_null=True,
        help_text="Id of one of the tenant's mapping profiles of the same integrator; null to send GRMS values as is.",
    )

    class Meta:
        model = Integration
        fields = (
            "id",
            "integrator",
            "hotel_id",
            "description",
            "access_token",
            "additional_info",
            "enable",
            "is_active",
            "tenant",
            "mapping_profile",
        )
        extra_kwargs = {
            "tenant": {"required": False, "allow_null": True},
            "is_active": {"read_only": True},
            "enable": {"read_only": True},
        }
        validators = [
            UniqueTogetherValidator(
                queryset=Integration.objects.filter(is_active=True),
                fields=("integrator", "tenant"),
                message="Integration with this integrator already exists for this tenant.",
            )
        ]

    def get_fields(self):
        fields = super().get_fields()
        if "tenant_id" in self.context:  # absent when drf-yasg builds the schema
            fields["mapping_profile"].queryset = MappingProfile.objects.by_tenant(self.context["tenant_id"])
        return fields

    def validate(self, attrs):
        # A request without mapping_profile keeps the current one, which must still fit the integrator.
        profile = attrs.get("mapping_profile", getattr(self.instance, "mapping_profile", None))
        if profile is None:
            return attrs
        integrator = attrs.get("integrator", getattr(self.instance, "integrator", None))
        if integrator is not None and profile.integrator_id != integrator.name:
            raise serializers.ValidationError({"mapping_profile": ["The profile belongs to another integrator."]})
        if self.instance:
            # The integration's overrides must fit the rules of the new profile.
            rules = profile.rules.select_related("tag_type").prefetch_related("tag_type__tag_ranges")
            rules_by_code = {rule.code: rule for rule in rules}
            errors = []
            for override in MappingOverride.objects.filter(integration=self.instance):
                errors += [
                    f"Override {override.pk}: {error}"
                    for error in override_errors(rules_by_code, override.rule_overrides)
                ]
            if errors:
                raise serializers.ValidationError({"mapping_profile": errors})
        return attrs


class IntegrationParams(ValidatorSerializer):
    SORT_FIELDS = ("created_at", "-created_at", "name", "-name")

    page = serializers.IntegerField(default=1)
    size = serializers.IntegerField(default=50)
    search_field = serializers.ChoiceField(choices=("name",), required=False)
    search_value = serializers.CharField(required=False)
    sort_by = serializers.ListField(child=serializers.ChoiceField(choices=SORT_FIELDS), required=False)
