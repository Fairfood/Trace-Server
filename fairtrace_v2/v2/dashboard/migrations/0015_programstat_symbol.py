# Generated by Django 2.2.6 on 2022-10-25 05:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0014_auto_20220921_1310'),
    ]

    operations = [
        migrations.AddField(
            model_name='programstat',
            name='symbol',
            field=models.CharField(blank=True, max_length=5, null=True),
        ),
    ]