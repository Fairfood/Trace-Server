# Generated by Django 2.2.6 on 2021-10-04 22:36
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("supply_chains", "0016_auto_20210712_1613"),
    ]

    operations = [
        migrations.AddField(
            model_name="farmer",
            name="id_no",
            field=models.CharField(
                blank=True, default="", max_length=100, null=True
            ),
        ),
    ]