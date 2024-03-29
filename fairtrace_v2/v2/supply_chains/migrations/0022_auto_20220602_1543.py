# Generated by Django 2.2.6 on 2022-06-02 10:13
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("supply_chains", "0021_auto_20220601_1514"),
    ]

    operations = [
        migrations.AddField(
            model_name="operation",
            name="name_en",
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="operation",
            name="name_es",
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="operation",
            name="name_fr",
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="operation",
            name="name_nl",
            field=models.CharField(max_length=100, null=True),
        ),
    ]
