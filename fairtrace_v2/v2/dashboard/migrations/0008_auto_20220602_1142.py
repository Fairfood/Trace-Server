# Generated by Django 2.2.6 on 2022-06-02 06:12
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0007_auto_20220602_1054"),
    ]

    operations = [
        migrations.RenameField(
            model_name="citheme",
            old_name="default_description",
            new_name="farmer_description",
        ),
        migrations.RenameField(
            model_name="citheme",
            old_name="default_description_en",
            new_name="farmer_description_en",
        ),
        migrations.RenameField(
            model_name="citheme",
            old_name="default_description_es",
            new_name="farmer_description_es",
        ),
        migrations.RenameField(
            model_name="citheme",
            old_name="default_description_fr",
            new_name="farmer_description_fr",
        ),
        migrations.RemoveField(
            model_name="citheme",
            name="default_description_nl",
        ),
        migrations.AddField(
            model_name="citheme",
            name="farmer_description_nl",
            field=models.TextField(blank=True, null=True),
        ),
    ]
