# Generated by Django 2.2.6 on 2023-03-15 07:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0017_citheme_show_brand_footer'),
    ]

    operations = [
        migrations.AddField(
            model_name='citheme',
            name='page_bg_colour',
            field=models.CharField(blank=True, default='#FFFFFF', max_length=20, null=True),
        ),
    ]
