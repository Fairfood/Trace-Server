# Generated by Django 2.2.6 on 2021-03-16 13:04
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("supply_chains", "0004_auto_20210315_0223"),
        ("products", "0003_auto_20210315_0223"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="nodeproduct",
            options={},
        ),
        migrations.AlterUniqueTogether(
            name="nodeproduct",
            unique_together={("product", "node_wallet")},
        ),
    ]
