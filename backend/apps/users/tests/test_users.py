from typing import cast

from django.urls import reverse

from rest_framework.response import Response as DRFResponse

from core.tests.base_test import BaseTestCase


class UserTest(BaseTestCase):
    fixtures = (
        "tenant_profile.yaml",
        "tenant.yaml",
        "roles_permissions.yaml",
        "users.yaml",
    )

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.angelina_token)

    def test_list(self):
        response = cast(DRFResponse, self.client.get(reverse("users:users-list")))

        if response.data is None:
            self.assertIsNotNone(response.data, "Expected response.data to be present")
            return

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data.get("results")[0]["id"], "e1fcc1ff-cce1-47e9-9952-88665815a9bd")
        self.assertEqual(response.data["results"][0]["first_name"], "Angelina")
        self.assertEqual(response.data["results"][0]["last_name"], "Jolie")
        self.assertEqual(response.data["results"][0]["email"], "angelina@gmail.com")
        self.assertEqual(response.data["results"][0]["additional_info"], None)
        self.assertEqual(response.data["results"][0]["phone"], "+999987654321")
        self.assertEqual(response.data["results"][0]["date_joined"], "2025-01-01T00:00:00")
        self.assertEqual(str(response.data["results"][0]["tenant"]), "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc")
        self.assertEqual(str(response.data["results"][0]["roles"][0]), "bb436b2a-2ff5-4835-a264-fe27e30710e6")
        self.assertEqual(response.data["results"][0]["is_active"], True)

    def test_create(self):
        # Case
        response = cast(DRFResponse, self.client.post(reverse("users:users-list"), {}))

        if response.data is None:
            self.assertIsNotNone(response.data, "Expected response.data to be present")
            return
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["email"], ["This field is required."])

        # Case
        response = cast(
            DRFResponse,
            self.client.post(
                reverse("users:users-list"),
                {
                    "email": "sysadmin@gmail.com",
                    "first_name": "sysadmin",
                    "last_name": "sysadmin",
                    "is_superuser": False,
                    "additional_info": {},
                    "phone": "+999123456789",
                    "tenant": "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc",
                    "roles": ["bb436b2a-2ff5-4835-a264-fe27e30710e6"],
                    "is_active": True,
                },
                format="json",
            ),
        )

        if response.data is None:
            self.assertIsNotNone(response.data, "Expected response.data to be present")
            return

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["email"], "sysadmin@gmail.com")
        self.assertEqual(response.data["first_name"], "sysadmin")
        self.assertEqual(response.data["last_name"], "sysadmin")
        self.assertEqual(response.data["is_superuser"], False)  # by default
        self.assertEqual(response.data["additional_info"], {})
        self.assertEqual(response.data["phone"], "+999123456789")
        self.assertEqual(str(response.data["tenant"]), "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc")
        self.assertEqual(str(response.data["roles"][0]), "bb436b2a-2ff5-4835-a264-fe27e30710e6")
        self.assertEqual(response.data["is_active"], True)

    def test_update(self):
        # Case - successful update
        user_id = "b1491621-9e9c-4dba-a743-119bac358781"
        update_data = {
            "email": "admin_updated@gmail.com",
            "first_name": "Updated",
            "last_name": "Admin",
            "additional_info": {"department": "IT"},
            "phone": "+999987654321",
            "tenant": "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc",
            "roles": ["bb436b2a-2ff5-4835-a264-fe27e30710e6"],
            "is_active": True,
        }

        response = cast(
            DRFResponse,
            self.client.put(
                reverse("users:users-detail", kwargs={"pk": user_id}),
                update_data,
                format="json",
            ),
        )

        if response.data is None:
            self.assertIsNotNone(response.data, "Expected response.data to be present")
            return

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "admin_updated@gmail.com")
        self.assertEqual(response.data["first_name"], "Updated")
        self.assertEqual(response.data["last_name"], "Admin")
        self.assertEqual(response.data["additional_info"], {"department": "IT"})
        self.assertEqual(response.data["phone"], "+999987654321")
        self.assertEqual(str(response.data["tenant"]), "ac73203f-e25f-4baa-a5c7-a4c9585f5bbc")
        self.assertEqual(str(response.data["roles"][0]), "bb436b2a-2ff5-4835-a264-fe27e30710e6")
        self.assertEqual(response.data["is_active"], True)

        # Case - non-existent user
        non_existent_id = "11111111-1111-1111-1111-111111111111"
        response = cast(
            DRFResponse,
            self.client.put(
                reverse("users:users-detail", kwargs={"pk": non_existent_id}),
                update_data,
                format="json",
            ),
        )
        self.assertEqual(response.status_code, 404)

        # Case - user from different tenant
        different_tenant_user_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
        response = cast(
            DRFResponse,
            self.client.put(
                reverse("users:users-detail", kwargs={"pk": different_tenant_user_id}),
                update_data,
                format="json",
            ),
        )
        self.assertEqual(response.status_code, 404)

    def test_delete(self):
        # Case - successful deletion
        user_id = "b1491621-9e9c-4dba-a743-119bac358781"
        response = cast(
            DRFResponse,
            self.client.delete(
                reverse("users:users-detail", kwargs={"pk": user_id}),
            ),
        )
        self.assertEqual(response.status_code, 204)

        # Verify user is actually deleted
        response = cast(
            DRFResponse,
            self.client.get(
                reverse("users:users-detail", kwargs={"pk": user_id}),
            ),
        )
        self.assertEqual(response.status_code, 404)

        # Case - non-existent user
        non_existent_id = "11111111-1111-1111-1111-111111111111"
        response = cast(
            DRFResponse,
            self.client.delete(
                reverse("users:users-detail", kwargs={"pk": non_existent_id}),
            ),
        )
        self.assertEqual(response.status_code, 404)

        # Case - user from different tenant
        different_tenant_user_id = "28c81921-f78e-4864-87d2-cec674f19d1c"
        response = cast(
            DRFResponse,
            self.client.delete(
                reverse("users:users-detail", kwargs={"pk": different_tenant_user_id}),
            ),
        )
        self.assertEqual(response.status_code, 404)
