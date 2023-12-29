# Generated by Django 2.2.6 on 2021-03-14 18:05
import django.db.models.deletion
import v2.blockchain.models.callback_auth
from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BlockchainRequest",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        blank=True, default=None, max_length=100, null=True
                    ),
                ),
                (
                    "object_related_name",
                    models.CharField(
                        blank=True, default=None, max_length=100, null=True
                    ),
                ),
                (
                    "receipt",
                    models.CharField(
                        blank=True, default=None, max_length=100, null=True
                    ),
                ),
                (
                    "status",
                    models.IntegerField(
                        choices=[(1, "Pending"), (2, "Completed")], default=1
                    ),
                ),
                ("updated_on", models.DateTimeField(auto_now=True)),
                ("created_on", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="BurnAssetRequest",
            fields=[
                (
                    "blockchainrequest_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="blockchain.BlockchainRequest",
                    ),
                ),
            ],
            bases=("blockchain.blockchainrequest",),
        ),
        migrations.CreateModel(
            name="CreateAssetRequest",
            fields=[
                (
                    "blockchainrequest_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="blockchain.BlockchainRequest",
                    ),
                ),
            ],
            bases=("blockchain.blockchainrequest",),
        ),
        migrations.CreateModel(
            name="CreateKeyRequest",
            fields=[
                (
                    "blockchainrequest_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="blockchain.BlockchainRequest",
                    ),
                ),
            ],
            bases=("blockchain.blockchainrequest",),
        ),
        migrations.CreateModel(
            name="TransferAssetRequest",
            fields=[
                (
                    "blockchainrequest_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="blockchain.BlockchainRequest",
                    ),
                ),
            ],
            bases=("blockchain.blockchainrequest",),
        ),
        migrations.CreateModel(
            name="CallBackToken",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "key",
                    models.CharField(
                        default=v2.blockchain.models.callback_auth.get_key,
                        max_length=200,
                    ),
                ),
                (
                    "status",
                    models.IntegerField(
                        choices=[(1, "Unused"), (2, "Used")], default=1
                    ),
                ),
                (
                    "expiry",
                    models.DateTimeField(
                        default=v2.blockchain.models.callback_auth.get_expiry
                    ),
                ),
                ("updated_on", models.DateTimeField(auto_now=True)),
                ("created_on", models.DateTimeField(auto_now_add=True)),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="blockchainrequest",
            name="callback_token",
            field=models.OneToOneField(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="request",
                to="blockchain.CallBackToken",
            ),
        ),
        migrations.AddField(
            model_name="blockchainrequest",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
