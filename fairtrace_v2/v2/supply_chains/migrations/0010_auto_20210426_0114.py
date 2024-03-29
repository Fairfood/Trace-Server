# Generated by Django 2.2.6 on 2021-04-25 19:44
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("supply_chains", "0009_auto_20210426_0002"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bulkexceluploads",
            name="farmers_added",
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="bulkexceluploads",
            name="farmers_to_add",
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="bulkexceluploads",
            name="farmers_to_update",
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="bulkexceluploads",
            name="farmers_updated",
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="bulkexceluploads",
            name="transactions_added",
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="bulkexceluploads",
            name="transactions_to_add",
            field=models.IntegerField(default=0),
        ),
    ]
