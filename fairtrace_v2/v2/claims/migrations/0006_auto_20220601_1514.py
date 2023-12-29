# Generated by Django 2.2.6 on 2022-06-01 09:44
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("claims", "0005_auto_20210404_2343"),
    ]

    operations = [
        migrations.AlterField(
            model_name="criterion",
            name="verifier",
            field=models.CharField(
                blank=True,
                choices=[
                    ("guji_traceable", "Traceable Guji Region Verifier"),
                    ("good_price", "Good Price Verifier"),
                    ("farmer", "Farmer verifier"),
                ],
                default=None,
                max_length=20,
                null=True,
            ),
        ),
    ]