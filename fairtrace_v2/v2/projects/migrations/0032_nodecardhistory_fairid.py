# Generated by Django 2.2.6 on 2025-03-18 13:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0031_auto_20250207_1551'),
    ]

    operations = [
        migrations.AddField(
            model_name='nodecardhistory',
            name='fairid',
            field=models.CharField(default='', max_length=500),
        ),
    ]
