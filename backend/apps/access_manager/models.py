from access_manager.querysets.card import CardQuerySet
from access_manager.querysets.group import GroupQuerySet, GroupRoomQuerySet
from access_manager.querysets.staff import StaffQuerySet
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q, UniqueConstraint

from core.models import BaseModel, CreatedByModel, UpdateByModel

DENIED = 0
GUEST = 1
HOUSEKEEPING = 2
ENGINEERING = 3
MASTER_CARD = 4
FAILED = 5


TYPE_CHOICES = (
    (DENIED, "DENIED"),
    (GUEST, "GUEST"),
    (HOUSEKEEPING, "HOUSEKEEPING"),
    (ENGINEERING, "ENGINEERING"),
    (MASTER_CARD, "MASTER CARD"),
    (FAILED, "FAILED"),
)


ALL_DAYS = "all_days"
MONDAY = "monday"
TUESDAY = "tuesday"
WEDNESDAY = "wednesday"
THURSDAY = "thursday"
FRIDAY = "friday"
SATURDAY = "saturday"
SUNDAY = "sunday"

WEEK_DAYS = (
    (ALL_DAYS, "ALL_DAYS"),
    (MONDAY, "MONDAY"),
    (TUESDAY, "TUESDAY"),
    (WEDNESDAY, "WEDNESDAY"),
    (THURSDAY, "THURSDAY"),
    (FRIDAY, "FRIDAY"),
    (SATURDAY, "SATURDAY"),
    (SUNDAY, "SUNDAY"),
)


class Group(BaseModel, CreatedByModel, UpdateByModel):
    name = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", on_delete=models.CASCADE)
    week_days = ArrayField(models.CharField(max_length=10, choices=WEEK_DAYS))
    start_time = models.TimeField()
    end_time = models.TimeField()
    expiry_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    additional_info = models.JSONField(null=True, blank=True)
    group_type = models.CharField(choices=TYPE_CHOICES, default=DENIED)

    objects = GroupQuerySet.as_manager()

    def __str__(self):
        return str(self.id)

    class Meta(BaseModel.Meta, CreatedByModel.Meta, UpdateByModel.Meta):
        db_table = "access_manager_groups"
        constraints = [
            UniqueConstraint(fields=["name", "tenant"], condition=Q(is_active=True), name="unique_card_group")
        ]


class Card(BaseModel, CreatedByModel, UpdateByModel):
    number = models.CharField(max_length=255)
    tenant = models.ForeignKey("main.Tenant", models.CASCADE)

    KNX = models.IntegerField(null=True, blank=True)
    additional_info = models.JSONField(null=True, blank=True)

    objects = CardQuerySet.as_manager()

    def __str__(self):
        return str(self.id)

    class Meta(BaseModel.Meta, CreatedByModel.Meta, UpdateByModel.Meta):
        db_table = "access_manager_cards"
        unique_together = ("number", "tenant")


class NeedSyncDevice(BaseModel, CreatedByModel):
    device = models.ForeignKey("main.Device", models.CASCADE)
    card = models.ForeignKey("access_manager.Card", models.CASCADE)
    need_sync = models.BooleanField(default=True)
    additional_info = models.JSONField(null=True, blank=True)

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "access_manager_need_sync_devices"


class Staff(BaseModel, CreatedByModel):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    group = models.ForeignKey("access_manager.Group", models.SET_NULL, null=True, blank=True)
    additional_info = models.JSONField(null=True, blank=True)

    tenant = models.ForeignKey("main.Tenant", models.CASCADE)

    objects = StaffQuerySet.as_manager()

    def __str__(self):
        return str(self.id)

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "access_manager_staff"
        constraints = [
            UniqueConstraint(
                fields=["tenant", "first_name", "last_name"], condition=Q(is_active=True), name="unique_staff"
            )
        ]


class StaffCard(BaseModel, CreatedByModel):
    staff = models.ForeignKey("access_manager.Staff", models.CASCADE)
    card = models.OneToOneField("access_manager.Card", models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "access_manager_staff_cards"


class GroupRoom(BaseModel, CreatedByModel):
    group = models.ForeignKey("access_manager.Group", models.CASCADE, "group_room")
    room = models.ForeignKey("main.Room", models.CASCADE, "group_room")
    additional_info = models.JSONField(null=True, blank=True)

    objects = GroupRoomQuerySet.as_manager()

    def __str__(self):
        return str(self.id)

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "access_manager_group_rooms"


class GroupPublicSpace(BaseModel, CreatedByModel):
    group = models.ForeignKey("access_manager.Group", models.CASCADE, "group_public_space")
    public_space = models.ForeignKey("main.PublicSpace", models.CASCADE, "group_public_space")
    additional_info = models.JSONField(null=True, blank=True)

    class Meta(BaseModel.Meta, CreatedByModel.Meta):
        db_table = "access_manager_group_public_spaces"

    def __str__(self):
        return f"{self.group} -> {self.public_space}"


class GuestPublicSpace(BaseModel):
    guest = models.ForeignKey("main.Guest", models.CASCADE)
    public_space = models.ForeignKey("main.PublicSpace", models.CASCADE)
    additional_info = models.JSONField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "access_manager_guest_public_spaces"

    def __str__(self):
        return f"{self.guest} -> {self.public_space}"
