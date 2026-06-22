from django.db.models import F, Prefetch, Q

from core.querysets.base_queryset import BaseQuerySet


class AttributeKvQuerySet(BaseQuerySet):
    VALUE_FIELDS = ("str_v", "bool_v", "json_v", "long_v", "dbl_v")

    @classmethod
    def _first_value(cls, row):
        return next((row[field] for field in cls.VALUE_FIELDS if row[field] is not None), None)

    def get_attributes(self, device, scope, sort_by=[]):
        rows = (
            self.filter(entity=device, attribute_type=scope)
            .annotate(key_name=F("attribute_key"))
            .values("last_update_ts", "key_name", *self.VALUE_FIELDS)
            .order_by(*sort_by)
        )
        return [
            {
                **{k: row[k] for k in ("last_update_ts", "key_name") if row[k] is not None},
                "value": self._first_value(row),
            }
            for row in rows
        ]

    def get_attributes_by_room(self, room, scope, sort_by=()):
        return (
            self.filter(entity__room=room, attribute_type=scope)
            .values("id", "attribute_key", "last_update_ts", *self.VALUE_FIELDS)
            .order_by(*sort_by)
        )

    def unique_keys_by_tenant(self, tenant_id, scope, tag_name: str | None = None):
        query = self.filter(attribute_key__icontains=tag_name) if tag_name else self
        query = (
            query.filter(entity__tenant_id=tenant_id, attribute_type=scope)
            .values_list("attribute_key", flat=True)
            .distinct()
        )
        return query.order_by("attribute_key")

    def update_or_create_or_delete(self, devices, room):
        from shuttle.models import AttributeKv

        for device in devices:
            self.update_or_create(
                entity_id=device.id,
                attribute_type=AttributeKv.SHARED_SCOPE,
                attribute_key="roomNumber",
                defaults={"str_v": room.number},
            )

        self.filter(entity__room=room, attribute_type=AttributeKv.SHARED_SCOPE, attribute_key="roomNumber").exclude(
            entity_id__in=devices
        ).update(str_v=None)

    def inactive_devices_in_spaces(self, tenant_id, sort_by="-last_update_ts"):
        from main.models import DevicePublicSpaces
        from shuttle.models import AttributeKv

        order = (sort_by,) if isinstance(sort_by, str) else tuple(sort_by or ("-last_update_ts",))

        qs = (
            self.filter(
                entity__tenant_id=tenant_id,
                attribute_type=AttributeKv.SERVER_SCOPE,
                attribute_key="active",
                bool_v=False,
            )
            .filter(Q(entity__room__isnull=False) | Q(entity__device_public_spaces__isnull=False))
            .select_related("entity", "entity__room", "entity__device_profile", "entity__tenant")
            .prefetch_related(
                Prefetch(
                    "entity__device_public_spaces",
                    queryset=DevicePublicSpaces.objects.select_related("public_space"),
                    to_attr="prefetched_device_public_spaces",
                ),
                Prefetch(
                    "entity__attribute_kvs",
                    queryset=AttributeKv.objects.filter(attribute_key="ipAddress").order_by("-last_update_ts"),
                    to_attr="prefetched_ip_attrs",
                ),
            )
            .order_by(*order)
            .distinct()
        )
        return qs
