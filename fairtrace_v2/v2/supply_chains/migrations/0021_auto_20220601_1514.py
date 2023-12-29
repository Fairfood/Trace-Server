# Generated by Django 2.2.6 on 2022-06-01 09:44
import v2.supply_chains.models.supply_chain
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("supply_chains", "0020_auto_20211118_1445"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bulkexceluploads",
            name="file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=v2.supply_chains.models.supply_chain._get_file_path,
            ),
        ),
        migrations.AlterField(
            model_name="supplychain",
            name="image",
            field=models.ImageField(
                blank=True,
                default=None,
                null=True,
                upload_to=v2.supply_chains.models.supply_chain._get_file_path,
            ),
        ),
    ]