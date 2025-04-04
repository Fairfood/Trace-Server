# Generated by Django 2.2.6 on 2024-03-10 19:28

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('supply_chains', '0045_auto_20240118_1058'),
        ('communications', '0005_auto_20230528_1257'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailConfiguration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('type', models.CharField(choices=[(5, 'Verify email'), (7, 'Reset password email'), (8, 'Magic login email'), (34, 'Admin magic login email'), (9, 'Invited as member'), (10, 'Node Invite'), (32, 'FFAdmin Invite'), (33, 'FFAdmin Existing Node Invite'), (11, 'Email Change'), (12, 'Existing Node Invite'), (30, 'Week One Reminder'), (31, 'Week Two Reminder'), (13, 'Received stock'), (14, 'Sent stock'), (15, 'Transaction Rejected'), (16, 'Received Stock Request'), (17, 'Decline Stock Request'), (22, 'Received Claim Request'), (23, 'Decline Claim Request'), (24, 'Received Information Request'), (25, 'Decline Information Request'), (26, 'Received Connection Request'), (18, 'Received verification Request'), (19, 'Approved claim'), (20, 'Rejected claim'), (21, 'Added comment'), (27, 'Decline Connection Request'), (28, 'Received Information Response'), (29, 'Received Claim Response')], max_length=50)),
                ('is_blocked', models.BooleanField(default=False)),
                ('creator', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_emailconfiguration_objects', to=settings.AUTH_USER_MODEL)),
                ('node', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='email_configurations', to='supply_chains.Node')),
                ('updater', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updater_emailconfiguration_objects', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='email_configurations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created_on',),
                'abstract': False,
            },
        ),
    ]
