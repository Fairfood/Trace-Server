# Generated by Django 2.2.6 on 2024-03-19 05:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0006_emailconfiguration'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailconfiguration',
            name='type',
            field=models.IntegerField(choices=[(5, 'Verify email'), (7, 'Reset password email'), (8, 'Magic login email'), (34, 'Admin magic login email'), (9, 'Invited as member'), (10, 'Node Invite'), (32, 'FFAdmin Invite'), (33, 'FFAdmin Existing Node Invite'), (11, 'Email Change'), (12, 'Existing Node Invite'), (30, 'Week One Reminder'), (31, 'Week Two Reminder'), (13, 'Received stock'), (14, 'Sent stock'), (15, 'Transaction Rejected'), (16, 'Received Stock Request'), (17, 'Decline Stock Request'), (22, 'Received Claim Request'), (23, 'Decline Claim Request'), (24, 'Received Information Request'), (25, 'Decline Information Request'), (26, 'Received Connection Request'), (18, 'Received verification Request'), (19, 'Approved claim'), (20, 'Rejected claim'), (21, 'Added comment'), (27, 'Decline Connection Request'), (28, 'Received Information Response'), (29, 'Received Claim Response')]),
        ),
    ]
