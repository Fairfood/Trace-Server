# Generated by Django 2.2.6 on 2025-03-20 07:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0020_batch_navigate_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='batch',
            name='gtin',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
