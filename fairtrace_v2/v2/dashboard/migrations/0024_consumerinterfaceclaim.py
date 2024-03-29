# Generated by Django 2.2.6 on 2023-07-03 04:32

import common.library
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('claims', '0010_claim_image'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dashboard', '0023_consumerinterfaceactor'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsumerInterfaceClaim',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('image', models.FileField(blank=True, upload_to=common.library._get_file_path)),
                ('description', models.CharField(blank=True, default='', max_length=500, null=True)),
                ('description_en', models.CharField(blank=True, default='', max_length=500, null=True)),
                ('description_es', models.CharField(blank=True, default='', max_length=500, null=True)),
                ('description_fr', models.CharField(blank=True, default='', max_length=500, null=True)),
                ('description_nl', models.CharField(blank=True, default='', max_length=500, null=True)),
                ('claim', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='claims.Claim')),
                ('creator', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_consumerinterfaceclaim_objects', to=settings.AUTH_USER_MODEL)),
                ('theme', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='claims', to='dashboard.CITheme')),
                ('updater', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updater_consumerinterfaceclaim_objects', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created_on',),
                'abstract': False,
            },
        ),
    ]
