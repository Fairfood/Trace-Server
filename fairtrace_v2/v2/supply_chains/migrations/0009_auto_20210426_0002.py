# Generated by Django 2.2.6 on 2021-04-25 18:32
import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("supply_chains", "0008_bulkexceluploads"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bulkexceluploads",
            name="supply_chain",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bulk_uploads",
                to="supply_chains.SupplyChain",
            ),
        ),
    ]