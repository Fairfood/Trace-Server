"""Commonly used third party libraries and functions."""
import plivo
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from sentry_sdk import capture_exception

from v2.communications.models import EmailConfiguration


def send_sms(mobile, message):
    """To send SMS."""
    try:
        # client = plivo.RestClient(
        #     settings.PLIVO_ID, settings.PLIVO_TOKEN)
        # response = client.messages.create(
        #     src='+6285574670328',
        #     dst=mobile,
        #     text=message,
        # )
        # print(response)
        # prints only the message_uuid
        # print(response.message_uuid)
        print("sending sms", message)
        pass

        return True
    except Exception as e:
        capture_exception(e)
        return False


def send_validation_email(validator):
    """To create Validator email."""
    html = render_to_string(
        validator.email_template(), {"validator": validator}
    )
    try:
        send_email.delay(
            validator.email_subject(),
            strip_tags(html),
            validator.email_from(),
            [validator.user.email],
            html,
        )
    except Exception as e:
        capture_exception(e)
    return True


def send_notification_email(
    notification, event, email_template, from_email, context=None
):
    """To create Validator email."""
    context = context if context else {}
    html = render_to_string(
        email_template,
        {"event": event, "notification": notification, "context": context},
    )
    to_email = notification.to_email
    node = notification.target_node
    unsubscribed = _check_unsubscribed_emails(
        notification.type, to_email, node)
    if unsubscribed:
        print("Email is unsubscribed.")
        return False
    
    if not to_email:
        print("No email address.")
        return False
    try:
        send_email.delay(
            notification.title_en,
            strip_tags(html),
            from_email,
            [to_email],
            html,
        )
    except Exception as e:
        capture_exception(e)
    return True


def send_push_notification(notification):
    """To send push notification."""
    for device in notification.devices.all():
        return None
        # try:
        #     device.send_message(
        #         title=notification.title_en,
        #         body=notification.body_en,
        #         # click_action=push_dict['click_action'],
        #         click_action='FCM_PLUGIN_ACTIVITY',
        #         sound='default',
        #         icon='',
        #         data={
        #             'type': notification.type,
        #             'title': notification.title_en,
        #             'body': notification.body_en
        #         })
        # except Exception as e:
        #     capture_exception(e)
        #     message = 'Failed to send push %s to device %s' % (
        #         notification.id, device.id)
        #     capture_message(message)
        #     pass

def _check_unsubscribed_emails(_type, email, node):
    """Check if email is unsubscribed."""
    if node:
        configs = EmailConfiguration.objects.filter(
            type=_type, is_blocked=True, email=email, node=node)
    else:
        return False
    return configs.exists()


@shared_task(name="send_email", queue="high")
def send_email(subject, text, email_from, to_emails, html):
    """Function to send emails.

    Input Params:
        mail_dict(dict): collection dictionary with following details,
            to(list): list of to email ids.
            subject(str): email subject.
            text(str): text content
            html(str): html file
            from: from address
    Return:
        success response
    """
    try:
        send_mail(
            subject,
            text,
            email_from,
            to_emails,
            fail_silently=False,
            html_message=html,
        )
    except Exception as e:
        capture_exception(e)


def send_farmer_sms(mobile, message, sender="+6285574670328"):
    """Function to send SMS same as the one defined.

    Duplicating to avoid test sms sending integrated in the existing
    functions
    """
    try:
        client = plivo.RestClient(settings.PLIVO_ID, settings.PLIVO_TOKEN)
        response = client.messages.create(
            src=sender,
            dst=mobile,
            text=message,
        )
        print(response)

        print(response.message_uuid)
        print("sending sms", message)
        return True
    except Exception as e:
        capture_exception(e)
        return False
