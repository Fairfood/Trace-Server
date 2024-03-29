# Generated by Django 2.2.6 on 2021-04-04 18:15
import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("blockchain", "0008_auto_20210403_1551"),
        ("transactions", "0002_auto_20210315_0223"),
    ]

    operations = [
        migrations.AddField(
            model_name="externaltransaction",
            name="submit_message_request",
            field=models.OneToOneField(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transactions_externaltransaction_msg_req",
                to="blockchain.BlockchainRequest",
            ),
        ),
    ]
