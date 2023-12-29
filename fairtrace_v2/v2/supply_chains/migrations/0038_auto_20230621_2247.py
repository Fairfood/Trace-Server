# Generated by Django 2.2.6 on 2023-06-21 17:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('supply_chains', '0037_uploadfarmermapping'),
    ]

    operations = [
        migrations.AlterField(
            model_name='node',
            name='type',
            field=models.IntegerField(choices=[(1, 'Company'), (2, 'Farmer'), (3, 'Verifier'), (4, 'Unknown')]),
        ),
        migrations.AlterField(
            model_name='operation',
            name='node_type',
            field=models.IntegerField(choices=[(1, 'Company'), (2, 'Farmer'), (3, 'Verifier'), (4, 'Unknown')]),
        ),
    ]
