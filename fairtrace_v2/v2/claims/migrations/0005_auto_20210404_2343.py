# Generated by Django 2.2.6 on 2021-04-04 18:13
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("claims", "0004_auto_20210404_2343"),
    ]

    operations = [
        migrations.RenameField(
            model_name="attachedclaim",
            old_name="block_chain_request",
            new_name="submit_message_request",
        ),
    ]