# Generated by Django 2.2.6 on 2023-06-19 14:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0020_auto_20230316_1218'),
    ]

    operations = [
        migrations.AddField(
            model_name='consumerinterfacestage',
            name='title_en',
            field=models.CharField(blank=True, default='', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='consumerinterfacestage',
            name='title_es',
            field=models.CharField(blank=True, default='', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='consumerinterfacestage',
            name='title_fr',
            field=models.CharField(blank=True, default='', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='consumerinterfacestage',
            name='title_nl',
            field=models.CharField(blank=True, default='', max_length=100, null=True),
        ),
    ]
