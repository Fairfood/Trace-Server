# Generated by Django 2.2.6 on 2022-12-22 05:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0013_nodecardhistory'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectproduct',
            name='premiums',
            field=models.ManyToManyField(blank=True, to='projects.ProjectPremium'),
        ),
    ]
