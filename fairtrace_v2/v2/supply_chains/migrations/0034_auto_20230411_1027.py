# Generated by Django 2.2.6 on 2023-04-11 04:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('supply_chains', '0033_auto_20230411_1026'),
    ]

    operations = [
        migrations.AlterField(
            model_name='farmerreference',
            name='number',
            field=models.CharField(max_length=100),
        ),
    ]