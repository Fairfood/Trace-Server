# Generated by Django 2.2.6 on 2024-02-05 09:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bulk_uploads', '0014_auto_20240118_1058'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasheetuploadsummary',
            name='total_price',
            field=models.IntegerField(default=0),
        ),
    ]
