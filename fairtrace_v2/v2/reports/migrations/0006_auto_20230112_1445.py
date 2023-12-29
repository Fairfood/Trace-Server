# Generated by Django 2.2.6 on 2023-01-12 09:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0005_auto_20221207_1326'),
    ]

    operations = [
        migrations.AlterField(
            model_name='export',
            name='export_type',
            field=models.IntegerField(choices=[(1, 'STOCK'), (2, 'EXTERNAL_TRANSACTION'), (3, 'INTERNAL_TRANSACTION'), (4, 'CONNECTIONS'), (5, 'FARMER'), (6, 'COMPANY'), (7, 'ADMIN_COMPANY'), (8, 'ADMIN_FARMER'), (9, 'ADMIN_EXTERNAL_TRANSACTION')]),
        ),
        migrations.AlterField(
            model_name='export',
            name='node',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='supply_chains.Node'),
        ),
    ]
