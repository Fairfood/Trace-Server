# Generated by Django 2.2.6 on 2024-01-18 05:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bulk_uploads', '0013_auto_20230906_1140'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasheetuploadsummary',
            name='total_price',
            field=models.CharField(default='0', max_length=255),
        ),
    ]
