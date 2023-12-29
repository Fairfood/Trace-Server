# Generated by Django 2.2.6 on 2021-05-15 16:41
import common.library
import django.db.models.deletion
from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("products", "0011_auto_20210426_2024"),
        ("supply_chains", "0014_wallettokenassociation_association_confirmed"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Project",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("updated_on", models.DateTimeField(auto_now=True)),
                ("created_on", models.DateTimeField(auto_now_add=True)),
                (
                    "name",
                    models.CharField(
                        blank=True, default="", max_length=100, null=True
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        blank=True, default="", max_length=2000, null=True
                    ),
                ),
                (
                    "image",
                    models.FileField(
                        blank=True,
                        default=None,
                        null=True,
                        upload_to=common.library._get_file_path,
                    ),
                ),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="creator_project_objects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_on",),
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ProjectProduct",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("updated_on", models.DateTimeField(auto_now=True)),
                ("created_on", models.DateTimeField(auto_now_add=True)),
                (
                    "image",
                    models.FileField(
                        blank=True,
                        default=None,
                        null=True,
                        upload_to=common.library._get_file_path,
                    ),
                ),
                (
                    "price",
                    models.FloatField(blank=True, default=None, null=True),
                ),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="creator_projectproduct_objects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="project_objects",
                        to="products.Product",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="product_objects",
                        to="projects.Project",
                    ),
                ),
                (
                    "updater",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="updater_projectproduct_objects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_on",),
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ProjectPremium",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("updated_on", models.DateTimeField(auto_now=True)),
                ("created_on", models.DateTimeField(auto_now_add=True)),
                (
                    "name",
                    models.CharField(
                        blank=True, default="", max_length=100, null=True
                    ),
                ),
                (
                    "type",
                    models.IntegerField(
                        choices=[
                            (101, "Per transaction"),
                            (201, "Per KG"),
                            (301, "Per unit currency"),
                            (401, "Per farmer"),
                        ],
                        default=301,
                    ),
                ),
                ("dependant_on_card", models.BooleanField(default=False)),
                (
                    "amount",
                    models.FloatField(blank=True, default=None, null=True),
                ),
                ("included", models.BooleanField(default=True)),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="creator_projectpremium_objects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updater",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="updater_projectpremium_objects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_on",),
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ProjectNode",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("updated_on", models.DateTimeField(auto_now=True)),
                ("created_on", models.DateTimeField(auto_now_add=True)),
                (
                    "connection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="supply_chains.Connection",
                    ),
                ),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="creator_projectnode_objects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "node",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participating_project_objects",
                        to="supply_chains.Node",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="member_objects",
                        to="projects.Project",
                    ),
                ),
                (
                    "updater",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="updater_projectnode_objects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_on",),
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="project",
            name="member_nodes",
            field=models.ManyToManyField(
                related_name="participating_projects",
                through="projects.ProjectNode",
                to="supply_chains.Node",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="owned_projects",
                to="supply_chains.Node",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="products",
            field=models.ManyToManyField(
                related_name="projects",
                through="projects.ProjectProduct",
                to="products.Product",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="supply_chain",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="projects",
                to="supply_chains.SupplyChain",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updater_project_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
