# Generated by Django 2.2.6 on 2021-04-05 19:45
import django.db.models.deletion
from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("supply_chains", "0004_auto_20210315_0223"),
        ("blockchain", "0008_auto_20210403_1551"),
        ("products", "0008_batch_blockchain_migration_on"),
    ]

    operations = [
        migrations.CreateModel(
            name="BatchMigration",
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
                ("updated_on", models.DateTimeField(auto_now=True)),
                ("created_on", models.DateTimeField(auto_now_add=True)),
                ("migrated_quantity", models.FloatField(default=0.0)),
                (
                    "unit",
                    models.IntegerField(
                        choices=[(1, "KG"), (2, "Tonne")], default=1
                    ),
                ),
                (
                    "blockchain_id",
                    models.CharField(
                        blank=True, default="", max_length=200, null=True
                    ),
                ),
                (
                    "blockchain_hash",
                    models.CharField(
                        blank=True, default="", max_length=2000, null=True
                    ),
                ),
                (
                    "info_message_id",
                    models.CharField(default="", max_length=500),
                ),
                (
                    "info_message_address",
                    models.CharField(default="", max_length=500),
                ),
                (
                    "prev_blockchain_id",
                    models.CharField(
                        blank=True, default="", max_length=200, null=True
                    ),
                ),
                (
                    "prev_blockchain_hash",
                    models.CharField(
                        blank=True, default="", max_length=2000, null=True
                    ),
                ),
                (
                    "prev_info_message_id",
                    models.CharField(default="", max_length=500),
                ),
                (
                    "prev_info_message_address",
                    models.CharField(default="", max_length=500),
                ),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="products.Batch",
                    ),
                ),
                (
                    "block_chain_request",
                    models.OneToOneField(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="products_batchmigration",
                        to="blockchain.BlockchainRequest",
                    ),
                ),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="creator_batchmigration_objects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "new_wallet",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="migrations_to",
                        to="supply_chains.BlockchainWallet",
                    ),
                ),
                (
                    "old_wallet",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="migrations_from",
                        to="supply_chains.BlockchainWallet",
                    ),
                ),
                (
                    "submit_message_request",
                    models.OneToOneField(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="products_batchmigration_msg_req",
                        to="blockchain.BlockchainRequest",
                    ),
                ),
                (
                    "updater",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="updater_batchmigration_objects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_on",),
                "abstract": False,
            },
        ),
    ]
