# Generated by Django 2.2.6 on 2022-06-20 09:27
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("supply_chains", "0025_node_available_languages"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="node",
            name="available_languages",
        ),
        migrations.AddField(
            model_name="nodemember",
            name="available_languages",
            field=models.CharField(default="en", max_length=500),
        ),
    ]
