# Generated by Django 2.2.6 on 2023-09-27 05:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('claims', '0011_claim_icon'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='claim',
            name='icon',
        ),
    ]