# Generated by Django 2.2.6 on 2024-01-12 14:18

from django.db import migrations
import django_extensions.db.fields.json


class Migration(migrations.Migration):

    dependencies = [
        ('supply_chains', '0042_node_external_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='farmerplot',
            name='coordinates',
            field=django_extensions.db.fields.json.JSONField(blank=True, default=dict, null=True),
        ),
    ]
