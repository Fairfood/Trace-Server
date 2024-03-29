# Generated by Django 2.2.6 on 2021-03-14 20:53
import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        (
            "blockchain",
            "0002_associatetokenrequest_callbackresponse_"
            "createtokenrequest_kyctokenrequest_submitmessagerequest_trans",
        ),
        ("claims", "0002_auto_20210314_2335"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="attachedbatchclaim",
            name="block_chain_request",
        ),
        migrations.RemoveField(
            model_name="claim",
            name="block_chain_request",
        ),
        migrations.AddField(
            model_name="attachedclaim",
            name="block_chain_request",
            field=models.OneToOneField(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="claims_attachedclaim",
                to="blockchain.BlockchainRequest",
            ),
        ),
        migrations.AddField(
            model_name="attachedclaim",
            name="blockchain_id",
            field=models.CharField(default="", max_length=500),
        ),
    ]
