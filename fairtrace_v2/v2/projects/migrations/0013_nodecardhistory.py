# Generated by Django 2.2.6 on 2022-08-17 14:22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('supply_chains', '0027_node_app_custom_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('projects', '0012_auto_20220623_1428'),
    ]

    operations = [
        migrations.CreateModel(
            name='NodeCardHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('card_id', models.CharField(max_length=500)),
                ('status', models.IntegerField(choices=[(101, 'Issued'), (201, 'Reissued'), (301, 'Removed')], default=101)),
                ('creator', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_nodecardhistory_objects', to=settings.AUTH_USER_MODEL)),
                ('node', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='card_history', to='supply_chains.Node')),
                ('updater', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updater_nodecardhistory_objects', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created_on',),
                'abstract': False,
            },
        ),
    ]