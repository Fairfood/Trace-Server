# Generated by Django 2.2.6 on 2021-03-14 21:48
import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("blockchain", "0003_auto_20210315_0223"),
    ]

    operations = [
        migrations.AddField(
            model_name="blockchainrequest",
            name="response",
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict),
        ),
    ]
