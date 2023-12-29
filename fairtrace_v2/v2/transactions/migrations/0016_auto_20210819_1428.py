# Generated by Django 2.2.6 on 2021-08-19 08:58
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("transactions", "0015_auto_20210805_2036"),
    ]

    operations = [
        migrations.AddField(
            model_name="externaltransaction",
            name="verification_latitude",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="externaltransaction",
            name="verification_longitude",
            field=models.FloatField(default=0.0),
        ),
    ]
