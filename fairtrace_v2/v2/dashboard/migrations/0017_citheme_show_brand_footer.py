# Generated by Django 2.2.6 on 2023-02-02 12:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0016_citheme_banner_mode'),
    ]

    operations = [
        migrations.AddField(
            model_name='citheme',
            name='show_brand_footer',
            field=models.BooleanField(default=False),
        ),
    ]