from typing import cast

from rest_framework.response import Response
from rest_framework.reverse import reverse

from core.tests.base_test import BaseTestCase


class PermissionsListViewTests(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)

    def test_permissions_list(self):
        response = cast(Response, self.client.get(reverse("users:permissions-list")))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data, "Expected response.data to be present")

        hidden_perms = [
            "session",
            "customer",
            "logentry",
            "taskresult",
            "groupresult",
            "contenttype",
            "chordcounter",
            "periodictask",
            "periodictasks",
            "tskvdictionary",
            "solarschedule",
            "clockedschedule",
            "crontabschedule",
            "intervalschedule",
            "devicecredentials",
        ]

        if response.data:
            for perm in hidden_perms:
                self.assertNotIn(perm, [p["codename"] for p in response.data])
