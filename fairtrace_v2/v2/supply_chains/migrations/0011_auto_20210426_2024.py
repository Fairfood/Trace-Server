# Generated by Django 2.2.6 on 2021-04-26 14:54
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("supply_chains", "0010_auto_20210426_0114"),
    ]

    operations = [
        migrations.AlterField(
            model_name="wallettopup",
            name="amount",
            field=models.DecimalField(
                decimal_places=5, default=0.0, max_digits=10
            ),
        ),
    ]
