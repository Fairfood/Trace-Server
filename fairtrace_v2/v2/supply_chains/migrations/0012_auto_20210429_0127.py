# Generated by Django 2.2.6 on 2021-04-28 19:57
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("supply_chains", "0011_auto_20210426_2024"),
    ]

    operations = [
        migrations.AlterField(
            model_name="wallettopup",
            name="amount",
            field=models.DecimalField(
                decimal_places=3, default=0.0, max_digits=5
            ),
        ),
    ]
