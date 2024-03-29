# Generated by Django 2.2.6 on 2021-04-26 14:54
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0010_auto_20210406_0151"),
    ]

    operations = [
        migrations.AlterField(
            model_name="batch",
            name="current_quantity",
            field=models.DecimalField(
                decimal_places=3, default=0.0, max_digits=25
            ),
        ),
        migrations.AlterField(
            model_name="batch",
            name="initial_quantity",
            field=models.DecimalField(
                decimal_places=3, default=0.0, max_digits=25
            ),
        ),
        migrations.AlterField(
            model_name="batchmigration",
            name="migrated_quantity",
            field=models.DecimalField(
                decimal_places=3, default=0.0, max_digits=25
            ),
        ),
    ]
