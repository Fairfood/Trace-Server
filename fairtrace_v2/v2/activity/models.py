from common.models import AbstractBaseModel
from django.db import models

from . import constants
from .content_manager import get_activity_text


# Create your models here.


class Activity(AbstractBaseModel):
    """Model to store activity."""

    user = models.ForeignKey(
        "accounts.FairfoodUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )
    node = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )
    supply_chain = models.ForeignKey(
        "supply_chains.SupplyChain",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )
    user_text = models.TextField(default="", null=True, blank=True)
    node_text = models.TextField(default="", null=True, blank=True)
    activity_type = models.IntegerField(
        choices=constants.ACTIVITY_TYPE_CHOICES,
        default=None,
        null=True,
        blank=True,
    )
    object_id = models.IntegerField()
    object_type = models.IntegerField(
        choices=constants.OBJECT_TYPE_CHOICES,
        default=None,
        null=True,
        blank=True,
    )

    def __str__(self):
        return "%s - %d" % (self.get_activity_type_display(), self.pk)

    @staticmethod
    def log(
        event,
        activity_type,
        object_id,
        object_type,
        user=None,
        node=None,
        supply_chain=None,
        context=None,
        prevent_duplication=True,
    ):
        """To log activity."""
        if not context:
            context = {}
        text = get_activity_text(activity_type, event, context)
        if prevent_duplication:
            activity, created = Activity.objects.get_or_create(
                user=user,
                node=node,
                supply_chain=supply_chain,
                user_text=text["user"],
                node_text=text["node"],
                activity_type=activity_type,
                object_id=object_id,
                object_type=object_type,
            )
        else:
            activity = Activity.objects.create(
                user=user,
                node=node,
                supply_chain=supply_chain,
                user_text=text["user"],
                node_text=text["node"],
                activity_type=activity_type,
                object_id=object_id,
                object_type=object_type,
            )
        return activity
