# Generated by Django 2.2.6 on 2021-08-05 14:43
import django.db.models.deletion
from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_auto_20210314_2335"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientVersion",
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
                    "client",
                    models.IntegerField(
                        choices=[(1, "Web"), (2, "App")], default=1
                    ),
                ),
                ("release_date", models.DateTimeField(blank=True, null=True)),
                ("last_active", models.DateTimeField(blank=True, null=True)),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="creator_clientversion_objects",
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
                        related_name="updater_clientversion_objects",
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
            name="UserClientVersion",
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
                ("last_active", models.DateTimeField(blank=True, null=True)),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="creator_userclientversion_objects",
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
                        related_name="updater_userclientversion_objects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_versions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "version",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="accounts.ClientVersion",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_on",),
                "abstract": False,
            },
        ),
    ]
