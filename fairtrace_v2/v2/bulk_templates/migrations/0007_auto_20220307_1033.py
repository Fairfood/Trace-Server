# Generated by Django 2.2.6 on 2022-03-07 05:03
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("bulk_templates", "0006_template_is_deleted"),
    ]

    operations = [
        migrations.AlterField(
            model_name="template",
            name="name",
            field=models.CharField(
                blank=True, default="", max_length=100, null=True
            ),
        ),
    ]
