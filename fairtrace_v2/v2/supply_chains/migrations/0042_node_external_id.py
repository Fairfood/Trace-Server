# Generated by Django 2.2.6 on 2023-11-28 04:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('supply_chains', '0041_auto_20230907_1034'),
    ]

    operations = [
        migrations.AddField(
            model_name='node',
            name='external_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
