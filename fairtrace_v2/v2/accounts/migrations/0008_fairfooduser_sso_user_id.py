# Generated by Django 2.2.6 on 2024-04-17 15:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_fairfooduser_external_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='fairfooduser',
            name='sso_user_id',
            field=models.CharField(default='Not Available', max_length=100),
        ),
    ]
