# Generated by Django 2.2.6 on 2021-03-14 18:05
import django.db.models.deletion
from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("products", "0001_initial"),
        ("supply_chains", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("dashboard", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="nodestats",
            name="node",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="stats",
                to="supply_chains.Node",
            ),
        ),
        migrations.AddField(
            model_name="nodestats",
            name="outdated_by",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="stats_reset",
                to="supply_chains.Node",
            ),
        ),
        migrations.AddField(
            model_name="nodestats",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updater_nodestats_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="menuitem",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="creator_menuitem_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="menuitem",
            name="theme",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="menu_items",
                to="dashboard.CITheme",
            ),
        ),
        migrations.AddField(
            model_name="menuitem",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updater_menuitem_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="dashboardtheme",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="creator_dashboardtheme_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="dashboardtheme",
            name="node",
            field=models.OneToOneField(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="dashboard_theme",
                to="supply_chains.Node",
            ),
        ),
        migrations.AddField(
            model_name="dashboardtheme",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updater_dashboardtheme_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="consumerinterfacestage",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="creator_consumerinterfacestage_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="consumerinterfacestage",
            name="operation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="stages",
                to="supply_chains.Operation",
            ),
        ),
        migrations.AddField(
            model_name="consumerinterfacestage",
            name="theme",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="stages",
                to="dashboard.CITheme",
            ),
        ),
        migrations.AddField(
            model_name="consumerinterfacestage",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updater_consumerinterfacestage_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="consumerinterfaceproduct",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="creator_consumerinterfaceproduct_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="consumerinterfaceproduct",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="products.Product",
            ),
        ),
        migrations.AddField(
            model_name="consumerinterfaceproduct",
            name="theme",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="products",
                to="dashboard.CITheme",
            ),
        ),
        migrations.AddField(
            model_name="consumerinterfaceproduct",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updater_consumerinterfaceproduct_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="citheme",
            name="batch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="themes",
                to="products.Batch",
            ),
        ),
        migrations.AddField(
            model_name="citheme",
            name="creator",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="creator_citheme_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="citheme",
            name="node",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="themes",
                to="supply_chains.Node",
            ),
        ),
        migrations.AddField(
            model_name="citheme",
            name="supply_chains",
            field=models.ManyToManyField(
                blank=True,
                related_name="themes",
                to="supply_chains.SupplyChain",
            ),
        ),
        migrations.AddField(
            model_name="citheme",
            name="updater",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updater_citheme_objects",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
