# Generated by Django 2.2.6 on 2023-06-14 04:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0020_auto_20230614_0955'),
    ]

    operations = [
        migrations.AlterField(
            model_name='premiumslab',
            name='premium',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='slabs', to='projects.ProjectPremium'),
        ),
    ]
