# Generated by Django 2.2.6 on 2023-07-06 06:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0023_auto_20230706_1200'),
    ]

    operations = [
        migrations.AddField(
            model_name='premiumoption',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='premiumoption',
            name='premium',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='projects.ProjectPremium'),
        ),
    ]
