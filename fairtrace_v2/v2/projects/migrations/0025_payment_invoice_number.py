# Generated by Django 2.2.6 on 2023-09-11 11:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0024_auto_20230706_1229'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='invoice_number',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
