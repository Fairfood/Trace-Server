# Generated by Django 2.2.6 on 2022-08-11 09:48

from django.db import migrations
import django_extensions.db.fields.json


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0017_auto_20220705_1507'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='extra_fields',
            field=django_extensions.db.fields.json.JSONField(blank=True, default=dict, null=True),
        ),
    ]
