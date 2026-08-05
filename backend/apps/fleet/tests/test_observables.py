from unittest.mock import patch

from django.test import TestCase

from fleet.models import FleetNode
from fleet.tasks import sweep_unconfirmed
from fleet.tests.factories import create_gateway, create_node, create_tenant


@patch("fleet.observables.fleet_node._send")
class FleetNodePublishTest(TestCase):
    """Every write to a node has to reach the subscribers, whatever made it."""

    def setUp(self):
        self.tenant = create_tenant()
        self.gateway = create_gateway(self.tenant)

    def tenants_published(self, send):
        published = set()
        for call in send.call_args_list:
            published |= set(call.args[0])
        return published

    def assert_published(self, send):
        self.assertEqual(self.tenants_published(send), {self.tenant.id})

    def test_create_publishes(self, send):
        with self.captureOnCommitCallbacks(execute=True):
            create_node(tenant=self.tenant, gateway=self.gateway)
        self.assert_published(send)

    def test_plain_save_publishes(self, send):
        node = create_node(tenant=self.tenant, gateway=self.gateway)
        send.reset_mock()

        with self.captureOnCommitCallbacks(execute=True):
            node.title = "Front desk"
            node.save(update_fields=["title", "updated_at"])

        self.assert_published(send)

    def test_soft_delete_publishes(self, send):
        """The delete endpoint only flips ``is_active``, so the row silently leaves the list."""
        node = create_node(tenant=self.tenant, gateway=self.gateway)
        send.reset_mock()

        with self.captureOnCommitCallbacks(execute=True):
            node.is_active = False
            node.save(update_fields=["is_active", "updated_at"])

        self.assert_published(send)

    def test_hard_delete_publishes(self, send):
        node = create_node(tenant=self.tenant, gateway=self.gateway)
        send.reset_mock()

        with self.captureOnCommitCallbacks(execute=True):
            node.delete()

        self.assert_published(send)

    def test_cascade_from_gateway_publishes(self, send):
        """
        ``gateway`` is CASCADE. Django fast-deletes cascaded rows with one silent
        ``DELETE`` unless a ``post_delete`` receiver is registered for the model.
        """
        create_node(tenant=self.tenant, gateway=self.gateway)
        send.reset_mock()

        with self.captureOnCommitCallbacks(execute=True):
            self.gateway.delete()

        self.assertFalse(FleetNode.objects.exists())
        self.assert_published(send)

    def test_bulk_update_publishes(self, send):
        """``QuerySet.update()`` fires no signal — the sweep has to publish by hand."""
        create_node(tenant=self.tenant, gateway=self.gateway, is_online=True)
        send.reset_mock()

        with self.captureOnCommitCallbacks(execute=True):
            sweep_unconfirmed([])

        self.assert_published(send)

    def test_bulk_update_that_touched_nothing_stays_quiet(self, send):
        create_node(tenant=self.tenant, gateway=self.gateway, is_online=False)
        send.reset_mock()

        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(sweep_unconfirmed([]), [])

        send.assert_not_called()

    def test_each_tenant_is_published_separately(self, send):
        other_tenant = create_tenant("Other")
        create_node(tenant=self.tenant, gateway=self.gateway, is_online=True)
        create_node(tenant=other_tenant, is_online=True)
        send.reset_mock()

        with self.captureOnCommitCallbacks(execute=True):
            sweep_unconfirmed([])

        self.assertEqual(self.tenants_published(send), {self.tenant.id, other_tenant.id})

    def test_nothing_is_published_until_the_transaction_commits(self, send):
        """
        The message carries no payload, so a subscriber that re-queries mid-transaction
        reads the pre-write state on its own connection and never hears again.
        """
        with self.captureOnCommitCallbacks(execute=False):
            create_node(tenant=self.tenant, gateway=self.gateway)
            send.assert_not_called()
