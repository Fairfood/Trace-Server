# Generated by Django 2.2.6 on 2024-01-17 10:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('supply_chains', '0043_farmerplot_coordinates'),
    ]

    operations = [
        migrations.RenameField(
            model_name='farmerplot',
            old_name='coordinates',
            new_name='geo_json',
        ),
    ]
