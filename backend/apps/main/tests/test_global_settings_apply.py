import json
from unittest.mock import MagicMock, patch

from django.urls import reverse

from core.tests.base import BaseTestCase
from main.models import Device, DeviceProfile, GlobalSettingsTemplate, Room
from main.services.global_settings import push_shared_attributes
from shuttle.models import AttributeKv, Relation

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"
TENANT_2_ID = "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc"
PUSH_TASK = "main.tasks.push_shared_attributes_task.delay"
PUBLISH_TASK = "shuttle.tasks.publish_updates_attribute_batch_task.delay"
CONFIG = {"temperature": 22, "eco_mode": True, "greeting": "Hello", "schedule": {"on": "08:00"}}


class GlobalSettingsDevicesMixin:
    def create_devices(self):
        self.profile = DeviceProfile.objects.create(name="default", type="DEFAULT", tenant_id=TENANT_ID)
        self.room_101 = Room.objects.create(number="101", floor="1", block="1", tenant_id=TENANT_ID)
        self.room_102 = Room.objects.create(number="102", floor="1", block="1", tenant_id=TENANT_ID)
        self.gateway = self.create_device("RCU-101", self.room_101, additional_info={"gateway": True})
        self.inactive = self.create_device("Old-101", self.room_101, is_active=False)
        self.sub_device = self.create_device("Thermostat-102", self.room_102)

    def create_device(self, name, room, **kwargs):
        return Device.objects.create(
            name=name, type="DEFAULT", tenant_id=TENANT_ID, device_profile=self.profile, room=room, **kwargs
        )


@patch(PUBLISH_TASK)
@patch(PUSH_TASK)
class ApplyGlobalSettingsTemplateTest(GlobalSettingsDevicesMixin, BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.bearer_token)
        self.url = reverse("main:global-settings-apply-preset")
        self.template = GlobalSettingsTemplate.objects.create(name="Default", config=CONFIG, tenant_id=TENANT_ID)
        self.create_devices()

    def apply(self, room_ids=None, template_id=None):
        payload = {
            "room_ids": [str(room_id) for room_id in (room_ids or [self.room_101.id])],
            "template_id": str(template_id or self.template.id),
        }
        with self.captureOnCommitCallbacks(execute=True):
            return self.post(self.url, data=payload, format="json")

    def attrs(self, device, scope):
        return {
            attr.attribute_key: attr.get_value
            for attr in AttributeKv.objects.filter(entity=device, attribute_type=scope)
        }

    def test_apply_writes_attributes(self, push, publish):
        response = self.apply()
        assert response.data is not None
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["devices"], [self.gateway.id])

        self.assertEqual(self.attrs(self.gateway, AttributeKv.SHARED_SCOPE), CONFIG)
        self.assertEqual(self.attrs(self.gateway, AttributeKv.SERVER_SCOPE), {"template_id": str(self.template.id)})
        self.assertEqual(self.attrs(self.inactive, AttributeKv.SHARED_SCOPE), {})
        self.assertEqual(self.attrs(self.sub_device, AttributeKv.SHARED_SCOPE), {})

        attr = AttributeKv.objects.get(entity=self.gateway, attribute_key="temperature")
        self.assertEqual(attr.long_v, 22)
        self.assertGreater(attr.last_update_ts, 10**12)  # milliseconds

    def test_apply_increments_used(self, push, publish):
        self.apply()
        self.apply(room_ids=[self.room_101.id, self.room_102.id])
        self.template.refresh_from_db()
        self.assertEqual(self.template.used, 2)

    def test_apply_dispatches_celery_tasks(self, push, publish):
        self.apply(room_ids=[self.room_101.id, self.room_102.id])

        device_ids, attributes = push.call_args.args
        self.assertCountEqual(device_ids, [str(self.gateway.id), str(self.sub_device.id)])
        self.assertEqual(attributes, CONFIG)

        updates = publish.call_args.args[0]
        self.assertCountEqual(updates.keys(), [f"{self.gateway.id}_{TENANT_ID}", f"{self.sub_device.id}_{TENANT_ID}"])
        keys = {(u["scope"], u["key_name"]) for u in updates[f"{self.gateway.id}_{TENANT_ID}"]}
        self.assertIn((AttributeKv.SERVER_SCOPE, "template_id"), keys)
        self.assertIn((AttributeKv.SHARED_SCOPE, "temperature"), keys)

    def test_reapply_overwrites_value_and_type(self, push, publish):
        self.apply()
        other = GlobalSettingsTemplate.objects.create(name="Eco", config={"temperature": "low"}, tenant_id=TENANT_ID)

        self.apply(template_id=other.id)

        attr = AttributeKv.objects.get(
            entity=self.gateway, attribute_type=AttributeKv.SHARED_SCOPE, attribute_key="temperature"
        )
        self.assertEqual(attr.str_v, "low")
        self.assertIsNone(attr.long_v)
        self.assertEqual(self.attrs(self.gateway, AttributeKv.SERVER_SCOPE), {"template_id": str(other.id)})

    def test_room_without_devices(self, push, publish):
        room = Room.objects.create(number="103", floor="1", block="1", tenant_id=TENANT_ID)
        response = self.apply(room_ids=[room.id])
        assert response.data is not None
        self.assertEqual(response.data["devices"], [])
        push.assert_not_called()
        publish.assert_not_called()
        self.template.refresh_from_db()
        self.assertEqual(self.template.used, 0)

    def test_empty_config_still_sets_template_id(self, push, publish):
        empty = GlobalSettingsTemplate.objects.create(name="Empty", config={}, tenant_id=TENANT_ID)
        self.apply(template_id=empty.id)
        self.assertEqual(self.attrs(self.gateway, AttributeKv.SERVER_SCOPE), {"template_id": str(empty.id)})
        push.assert_not_called()

    def test_template_of_another_tenant_is_rejected(self, push, publish):
        foreign = GlobalSettingsTemplate.objects.create(name="Foreign", tenant_id=TENANT_2_ID)
        response = self.apply(template_id=foreign.id)
        self.assertEqual(response.status_code, 400)

    def test_unknown_template_is_rejected(self, push, publish):
        response = self.apply(template_id="11111111-1111-1111-1111-111111111111")
        self.assertEqual(response.status_code, 400)

    def test_room_of_another_tenant_is_rejected(self, push, publish):
        foreign = Room.objects.create(number="101", floor="1", block="1", tenant_id=TENANT_2_ID)
        response = self.apply(room_ids=[self.room_101.id, foreign.id])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.attrs(self.gateway, AttributeKv.SHARED_SCOPE), {})
        self.template.refresh_from_db()
        self.assertEqual(self.template.used, 0)

    def test_empty_room_ids_are_rejected(self, push, publish):
        response = self.post(self.url, data={"room_ids": [], "template_id": str(self.template.id)}, format="json")
        self.assertEqual(response.status_code, 400)


class PushSharedAttributesTest(GlobalSettingsDevicesMixin, BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml")

    def setUp(self):
        self.create_devices()
        Relation.objects.create(
            from_id=self.gateway,
            from_type="DEVICE",
            to_id=self.sub_device,
            to_type="DEVICE",
            relation_type_group="COMMON",
            relation_type="Contains",
        )

    @patch("main.services.global_settings.connect_to_rabbitmq")
    def test_push_uses_one_connection(self, connect):
        channel = MagicMock()
        connect.return_value = channel

        push_shared_attributes([str(self.gateway.id), str(self.sub_device.id)], {"temperature": 22})

        connect.assert_called_once()
        channel.connection.close.assert_called_once()
        messages = {
            msg["targetDeviceUUID"] + msg["topic"]: msg
            for msg in (json.loads(c.kwargs["body"]) for c in channel.basic_publish.call_args_list)
        }
        self.assertEqual(len(messages), 2)
        direct = messages[f"{self.gateway.id}v1/devices/me/attributes"]
        self.assertEqual(direct["data"], {"temperature": 22})
        via_gateway = messages[f"{self.gateway.id}v1/gateway/attributes"]
        self.assertEqual(via_gateway["data"], {"device": "Thermostat-102", "data": {"temperature": 22}})

    @patch("main.services.global_settings.connect_to_rabbitmq")
    def test_sub_device_without_gateway_is_skipped(self, connect):
        channel = MagicMock()
        connect.return_value = channel
        orphan = self.create_device("Lock-102", self.room_102)

        push_shared_attributes([str(orphan.id)], {"temperature": 22})

        channel.basic_publish.assert_not_called()
        channel.connection.close.assert_called_once()
