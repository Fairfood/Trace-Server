# Generated by Django 2.2.6 on 2023-09-06 06:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bulk_uploads', '0012_auto_20230817_1504'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='datasheettemplatefield',
            options={'ordering': ['id']},
        ),
    ]
