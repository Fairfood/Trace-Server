# Generated by Django 2.2.6 on 2021-04-05 17:56
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0007_auto_20210405_2322"),
    ]

    operations = [
        migrations.AddField(
            model_name="batch",
            name="blockchain_migration_on",
            field=models.DateTimeField(default=None, null=True),
        ),
    ]
