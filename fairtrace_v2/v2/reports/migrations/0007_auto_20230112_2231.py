# Generated by Django 2.2.6 on 2023-01-12 17:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0006_auto_20230112_1445'),
    ]

    operations = [
        migrations.AlterField(
            model_name='export',
            name='file_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]