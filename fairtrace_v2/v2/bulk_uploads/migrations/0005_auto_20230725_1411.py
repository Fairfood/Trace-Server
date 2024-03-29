# Generated by Django 2.2.6 on 2023-07-25 08:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bulk_uploads', '0004_auto_20230721_1007'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasheettemplate',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='datasheettemplate',
            name='data_row',
            field=models.IntegerField(default=1),
        ),
        migrations.AlterField(
            model_name='datasheettemplate',
            name='title_row',
            field=models.IntegerField(default=0),
        ),
    ]
