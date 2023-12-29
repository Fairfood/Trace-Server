"""Models of the app Citizen.

All models related to the User Accounts are managed in this app.
"""
from __future__ import unicode_literals

from common import vendors
from common.models import AbstractBaseModel
from django.conf import settings
from django.contrib.postgres import fields
from django.db import models
from django.db import transaction
from v2.activity.constants import OBJECT_TYPE_CHOICES
from v2.communications.constants import NOTIF_ACTION_CHOICES
from v2.communications.constants import NOTIF_ACTION_NORMAL
from v2.communications.constants import NOTIF_TYPE_CHOICES
from v2.communications.content_manager import get_content
from v2.communications.content_manager import (
    INACTIVE_NODE_NOTIFICATION_TEMPLATE,
)

from . import constants
from ..accounts.constants import VTOKEN_STATUS_UNUSED
from .constants import NOTIF_ACTION_EMAIL
from .constants import NOTIF_ACTION_EMAIL_N_SMS
from .constants import NOTIF_ACTION_PUSH
from .constants import NOTIF_ACTION_PUSH_EMAIL_N_SMS
from .constants import NOTIF_ACTION_PUSH_N_EMAIL


class Notification(AbstractBaseModel):
    """Class for managing user notification.

    Attribs:
        user(obj): User object
        devices(objs): device to which notification initiated.
        is_read(bool): to mark if the notification is
            read by the user.
        title_en(str): notification message title in English.
        body_en(str): notification message body in English
        title_loc(str): notification message title in local language.
        body_loc(str): notification message body in local language
        action(int): notification type based on which
            sending emails or push notification is decided.
        event(int): notification event
        event_id(int): event id.
        type(int): notification type for identifying the notification
            when it is pushed to devices.
    """

    user = models.ForeignKey(
        "accounts.FairfoodUser",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    devices = models.ManyToManyField("accounts.UserDevice", blank=True)
    is_read = models.BooleanField(default=False)
    visibility = models.BooleanField(default=True)
    title_en = models.CharField(default="", max_length=300)
    title_loc = models.CharField(default="", max_length=300, blank=True)
    body_en = models.CharField(default="", max_length=500)
    body_loc = models.CharField(default="", max_length=500, blank=True)
    action_url = models.CharField(default="", max_length=500, blank=True)
    actor_node = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="actions",
    )
    target_node = models.ForeignKey(
        "supply_chains.Node",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="notifications",
    )
    action = models.IntegerField(
        default=NOTIF_ACTION_NORMAL, choices=NOTIF_ACTION_CHOICES
    )
    event = models.IntegerField(default=0, choices=OBJECT_TYPE_CHOICES)
    event_id = models.CharField(default="", max_length=50)
    type = models.IntegerField(default=0, choices=NOTIF_TYPE_CHOICES)
    context = fields.JSONField(null=True, blank=True)
    send_to = models.EmailField(null=True, blank=True, default="")
    supply_chain = models.ForeignKey(
        "supply_chains.SupplyChain",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    class Meta:
        """Meta class for the above model."""

        ordering = ("-created_on",)

    def __str__(self):
        """To return value in django admin."""
        return "%s-%s: %s" % (self.user.name, self.title_en, self.idencode)

    @staticmethod
    def notify(
        token,
        event,
        user,
        notif_type,
        supply_chain=None,
        actor_node=None,
        target_node=None,
        send_to="",
        context=None,
        sender=None,
    ):
        """To create notification of an event."""
        content = get_content(notif_type)
        context = {} if not context else context

        notification, created = Notification.objects.get_or_create(
            user=user,
            action=content["action"],
            event=content["event"],
            event_id=event.idencode,
            supply_chain=supply_chain,
            type=notif_type,
            send_to=send_to,
            actor_node=actor_node,
            target_node=target_node,
        )
        if created:
            notification.creator = event.creator
        else:
            notification.updater = event.creator
        if not sender:
            sender = (
                event.creator
            )  # Variable used in email templates and content_managers
        notification.title_en = content["title_en"].format(**vars())
        notification.title_loc = content["title_loc"].format(**vars())
        notification.body_en = content["body_en"].format(**vars())
        notification.body_loc = content["body_loc"].format(**vars())
        notification.visibility = content["visibility"]
        notification.context = context
        notification.action_url = content["action_url"].format(**vars())
        notification.action_url += f"&email={user.email}"

        if not token and not user.email_verified:
            from v2.accounts.models import ValidationToken
            from v2.accounts.constants import VTOKEN_TYPE_NOTIFICATION

            token = ValidationToken.objects.filter(
                user=user,
                creator=event.creator,
                type=VTOKEN_TYPE_NOTIFICATION,
                status=VTOKEN_STATUS_UNUSED,
            ).last()
            if not token:
                token = ValidationToken.initialize(
                    user=user,
                    creator=event.creator,
                    type=VTOKEN_TYPE_NOTIFICATION,
                )

        if token:
            notification.action_url += (
                f"&token={token.key}" f"&salt={token.idencode}"
            )
        notification.save()
        for device in user.devices():
            notification.devices.add(device)

        notification.send(event)

        return notification

    def send(self, event):
        """Send notification."""

        content = get_content(self.type)
        template_name = content["email_template"]
        from_email = content["from_email"]
        resend_old_invites = False

        if self.target_node and not self.target_node.date_joined:
            # If the node has not been joined, a different email is to be sent.
            if not self.target_node.date_invited:
                # Any pending invites should also be sent, along with the
                # request to map suppliers when the first invite is sent.
                resend_old_invites = True
            if self.type not in [
                constants.NOTIF_TYPE_WEEK_ONE_REMINDER,
                constants.NOTIF_TYPE_WEEK_TWO_REMINDER,
                constants.NOTIF_TYPE_FFADMIN_NEW_NODE_INVITE,
                constants.NOTIF_TYPE_NEW_NODE_INVITE,
                constants.NOTIF_TYPE_FFADMIN_EXISTING_NODE_INVITE,
            ]:
                template_name = INACTIVE_NODE_NOTIFICATION_TEMPLATE
                self.context["other_notification_count"] = (
                    self.user.notifications.filter(is_read=False).count() - 1
                )
                self.save()

        email_template = settings.TEMPLATES_DIR + template_name

        if self.action == NOTIF_ACTION_EMAIL:
            vendors.send_notification_email(
                self, event, email_template, from_email, self.context
            )
        elif self.action == NOTIF_ACTION_PUSH:
            vendors.send_push_notification(self)
        elif self.action == NOTIF_ACTION_PUSH_N_EMAIL:
            vendors.send_push_notification(self)
            vendors.send_notification_email(
                self, event, email_template, from_email, self.context
            )
        elif self.action == NOTIF_ACTION_PUSH_EMAIL_N_SMS:
            vendors.send_push_notification(self)
            vendors.send_sms(self.user.phone, self.body_en)
            vendors.send_notification_email(
                self, event, email_template, from_email, self.context
            )
        elif self.action == NOTIF_ACTION_EMAIL_N_SMS:
            vendors.send_sms(self.user.phone, self.body_en)
            vendors.send_notification_email(
                self, event, email_template, from_email, self.context
            )

        if resend_old_invites:
            transaction.on_commit(
                lambda: self.target_node.send_pending_invites()
            )

    def read(self):
        """To read notification."""
        self.is_read = True
        self.save()

    @property
    def to_email(self):
        """Return to email.

        Defaults to user's email if send_to is not specified. Created to
        managed email verification for email changes.
        """
        if self.send_to:
            return self.send_to
        return self.user.email
