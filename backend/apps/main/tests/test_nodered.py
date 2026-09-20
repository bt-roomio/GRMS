import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import override_settings

from core.tests.base import BaseTestCase
from main.models import Tenant
from main.services.nodered import (
    deprovision_nodered,
    env_path,
    nodered_host,
    provision_nodered,
    read_env,
    reclaim_slug,
    removed_env_path,
    resolve_slug,
    write_env,
)
from main.services.tenant_provisioning import provision_tenant

TENANT_ID = "28c81921-f78e-4864-87d2-cec674f19d1c"

TEMPLATE = """# Node-RED tenant env
TENANT_NAME=nines
NODERED_TENANT_ID=00000000-0000-0000-0000-000000000000
NODERED_VIRTUAL_HOST=nodered-nines.example.com
LETSENCRYPT_EMAIL=grms@room.io
NODERED_LOG_LEVEL=warn
TZ=Asia/Nicosia
"""


class NodeRedServiceTest(BaseTestCase):
    fixtures = ("tenant_profile.yaml", "tenant.yaml", "roles_permissions.yaml", "users.yaml")

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.deploy_dir = Path(tmp.name)
        (self.deploy_dir / ".env.nodered.example").write_text(TEMPLATE)

        settings_override = override_settings(
            NODERED_DEPLOY_DIR=tmp.name,
            FRONTEND_DOMAIN="https://cloud.room.io",
            NODERED_DNS_TARGET="api.cloud.room.io",
            NODERED_BASE_DOMAIN="",
            LETSENCRYPT_EMAIL="ops@room.io",
        )
        settings_override.enable()
        self.addCleanup(settings_override.disable)

        self.tenant = Tenant.objects.get(id=TENANT_ID)
        self.tenant.title = "Flamingo Hotel"
        self.tenant.save()

    def test_env_file_fills_template_and_keeps_defaults(self):
        path = write_env("flamingo-hotel", self.tenant, "flamingo-hotel.nodered.cloud.room.io")

        values = read_env(path)
        self.assertEqual(path.name, ".env.nodered.flamingo-hotel")
        self.assertEqual(values["TENANT_NAME"], "flamingo-hotel")
        self.assertEqual(values["NODERED_TENANT_ID"], TENANT_ID)
        self.assertEqual(values["NODERED_VIRTUAL_HOST"], "flamingo-hotel.nodered.cloud.room.io")
        self.assertEqual(values["LETSENCRYPT_EMAIL"], "ops@room.io")
        self.assertEqual(values["TZ"], "Asia/Nicosia")
        self.assertIn("# Node-RED tenant env", path.read_text())

    def test_env_file_is_readable_by_the_host_operator(self):
        """Written from a root container, it still has to be readable on the host."""
        path = write_env("flamingo-hotel", self.tenant, "flamingo-hotel.nodered.cloud.room.io")
        self.assertEqual(path.stat().st_mode & 0o777, 0o644)

    def test_base_domain_overrides_the_frontend_one(self):
        with override_settings(NODERED_BASE_DOMAIN="https://bukhara.cloud"):
            self.assertEqual(nodered_host("flamingo-hotel"), "flamingo-hotel.nodered.bukhara.cloud")
        self.assertEqual(nodered_host("flamingo-hotel"), "flamingo-hotel.nodered.cloud.room.io")

    def test_slug_of_a_live_namesake_gets_the_tenant_id(self):
        env_path("flamingo-hotel").write_text("NODERED_TENANT_ID=11111111-1111-1111-1111-111111111111\n")
        self.assertEqual(resolve_slug(self.tenant), f"flamingo-hotel-{self.tenant.id.hex[:8]}")

    def test_slug_of_a_deleted_tenant_is_free_again(self):
        removed_env_path("flamingo-hotel").write_text("NODERED_TENANT_ID=11111111-1111-1111-1111-111111111111\n")
        self.assertEqual(resolve_slug(self.tenant), "flamingo-hotel")

    def test_own_slug_is_reused(self):
        env_path("flamingo-hotel").write_text(f"NODERED_TENANT_ID={TENANT_ID}\n")
        self.assertEqual(resolve_slug(self.tenant), "flamingo-hotel")

    @patch("main.services.nodered.subprocess.run")
    def test_reclaiming_a_name_drops_the_volume_of_the_previous_tenant(self, run):
        marker = removed_env_path("flamingo-hotel")
        marker.write_text("NODERED_TENANT_ID=11111111-1111-1111-1111-111111111111\n")
        run.return_value = MagicMock(returncode=0, stderr="")

        reclaim_slug("flamingo-hotel", TENANT_ID)

        self.assertEqual(run.call_args.args[0], ["docker", "volume", "rm", "nodered-flamingo-hotel_nodered_data"])
        self.assertFalse(marker.exists())

    @patch("main.services.nodered.subprocess.run")
    def test_own_marker_is_left_alone(self, run):
        marker = removed_env_path("flamingo-hotel")
        marker.write_text(f"NODERED_TENANT_ID={TENANT_ID}\n")

        reclaim_slug("flamingo-hotel", TENANT_ID)

        run.assert_not_called()
        self.assertTrue(marker.exists())

    @patch("main.services.nodered.subprocess.run")
    @patch("main.services.nodered.CloudflareClient")
    def test_provision_sets_node_url_and_keeps_general_settings(self, client, run):
        client.return_value.upsert_cname.return_value = {"id": "rec1"}
        client.return_value.zone_name.return_value = "cloud.room.io"

        provision_nodered(TENANT_ID)

        host = "flamingo-hotel.nodered.cloud.room.io"
        client.return_value.upsert_cname.assert_called_once()
        self.assertEqual(client.return_value.upsert_cname.call_args.args, (host, "api.cloud.room.io"))
        command = run.call_args.args[0]
        self.assertEqual(command[-2:], ["up", "-d"])
        self.assertIn("nodered-flamingo-hotel", command)

        info = Tenant.objects.get(id=TENANT_ID).additional_info
        self.assertEqual(info["general_settings"]["roomio_node_url"], f"https://{host}")
        self.assertTrue(info["general_settings"]["bathroom_enable"])
        self.assertEqual(info["nodered"]["status"], "ready")
        self.assertEqual(info["nodered"]["dns_record_id"], "rec1")
        self.assertTrue(env_path("flamingo-hotel").exists())

    @patch("main.services.nodered.subprocess.run")
    @patch("main.services.nodered.CloudflareClient")
    def test_compose_failure_is_recorded_and_raised(self, client, run):
        client.return_value.upsert_cname.return_value = {"id": "rec1"}
        client.return_value.zone_name.return_value = "cloud.room.io"
        run.side_effect = subprocess.CalledProcessError(1, ["docker"], stderr="pull access denied")

        with self.assertRaisesMessage(Exception, "pull access denied"):
            provision_nodered(TENANT_ID)

        info = Tenant.objects.get(id=TENANT_ID).additional_info
        self.assertEqual(info["nodered"]["status"], "failed")
        self.assertIn("pull access denied", info["nodered"]["error"])
        self.assertEqual(info["general_settings"]["roomio_node_url"], "")

    @patch("main.services.nodered.subprocess.run")
    @patch("main.services.nodered.CloudflareClient")
    def test_host_outside_the_cloudflare_zone_is_refused(self, client, run):
        client.return_value.zone_name.return_value = "bukhara.cloud"

        with self.assertRaisesMessage(Exception, "outside the Cloudflare zone"):
            provision_nodered(TENANT_ID)

        client.return_value.upsert_cname.assert_not_called()
        info = Tenant.objects.get(id=TENANT_ID).additional_info
        self.assertEqual(info["nodered"]["status"], "failed")

    @patch("main.services.nodered.subprocess.run")
    @patch("main.services.nodered.CloudflareClient")
    def test_deprovision_stops_container_and_drops_record(self, client, run):
        write_env("flamingo-hotel", self.tenant, "flamingo-hotel.nodered.cloud.room.io")

        deprovision_nodered("flamingo-hotel", "rec1")

        self.assertEqual(run.call_args.args[0][-1], "down")
        self.assertFalse(env_path("flamingo-hotel").exists())
        self.assertTrue(removed_env_path("flamingo-hotel").exists())
        client.return_value.delete_record.assert_called_once_with("rec1")

    @patch("main.tasks.provision_nodered_task.delay")
    def test_new_tenant_queues_provisioning_only_when_enabled(self, delay):
        with override_settings(NODERED_PROVISIONING_ENABLED=False), self.captureOnCommitCallbacks(execute=True):
            provision_tenant(title="Astoria", email="gm@astoria.uz", password="secret")
        delay.assert_not_called()

        with override_settings(NODERED_PROVISIONING_ENABLED=True), self.captureOnCommitCallbacks(execute=True):
            tenant = provision_tenant(title="Hilton", email="gm@hilton.uz", password="secret")
        delay.assert_called_once_with(str(tenant.id))
