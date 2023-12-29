# Generated by Django 2.2.6 on 2022-08-29 06:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0012_auto_20220829_0840'),
    ]

    operations = [
        migrations.RenameField(
            model_name='citheme',
            old_name='story_program',
            new_name='program',
        ),
        migrations.RenameField(
            model_name='programstat',
            old_name='story_program',
            new_name='program',
        ),
        migrations.AlterField(
            model_name='programstat',
            name='value',
            field=models.FloatField(default=0),
        ),
    ]
