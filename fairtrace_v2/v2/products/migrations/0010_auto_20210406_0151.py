# Generated by Django 2.2.6 on 2021-04-05 20:21
import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0009_batchmigration"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="batch",
            name="blockchain_migration_on",
        ),
        migrations.RemoveField(
            model_name="batch",
            name="topl_blockchain_hash",
        ),
        migrations.AlterField(
            model_name="batchmigration",
            name="batch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="migrations",
                to="products.Batch",
            ),
        ),
    ]
