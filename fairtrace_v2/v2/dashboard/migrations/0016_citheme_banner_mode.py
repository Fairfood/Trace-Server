# Generated by Django 2.2.6 on 2022-10-31 10:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0015_programstat_symbol'),
    ]

    operations = [
        migrations.AddField(
            model_name='citheme',
            name='banner_mode',
            field=models.IntegerField(choices=[(1, 'Half width banner'), (2, 'Full width banner')], default=1),
        ),
    ]
