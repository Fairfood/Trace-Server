# Generated by Django 2.2.6 on 2023-04-10 02:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def initialize(apps, schema):
    plot_model = apps.get_model('supply_chains', 'FarmerPlot')
    farmer_model = apps.get_model('supply_chains', 'Farmer')
    objs = []
    for farmer in farmer_model.objects.all():
        data = {'name': 'Plot 1',
                'farmer_id': farmer.id,
                'house_name': farmer.house_name,
                'street': farmer.street,
                'city': farmer.city,
                'sub_province': farmer.sub_province,
                'province': farmer.province,
                'country': farmer.country,
                'latitude': farmer.latitude,
                'longitude': farmer.longitude,
                'zipcode': farmer.zipcode,
                }
        objs.append(plot_model(**data))
    if objs:
        plot_model.objects.bulk_create(objs)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('supply_chains', '0030_farmerreference_reference'),
    ]

    operations = [
        migrations.CreateModel(
            name='FarmerPlot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('house_name', models.CharField(blank=True, default='', max_length=100)),
                ('street', models.CharField(blank=True, default='', max_length=500)),
                ('city', models.CharField(blank=True, default='', max_length=500)),
                ('sub_province', models.CharField(blank=True, default='', max_length=500)),
                ('province', models.CharField(blank=True, default='', max_length=500)),
                ('country', models.CharField(blank=True, default='', max_length=500)),
                ('latitude', models.FloatField(default=0.0)),
                ('longitude', models.FloatField(default=0.0)),
                ('zipcode', models.CharField(blank=True, default='', max_length=50)),
                ('name', models.CharField(max_length=20)),
                ('location_type', models.CharField(choices=[('APPROXIMATE', 'APPROXIMATE'), ('POLYGON', 'POLYGON'), ('ACCURATE', 'ACCURATE')], default='APPROXIMATE', max_length=20)),
                ('total_plot_area', models.DecimalField(decimal_places=4, default=0, max_digits=10)),
                ('crop_types', models.TextField(blank=True, null=True)),
                ('creator', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_farmerplot_objects', to=settings.AUTH_USER_MODEL)),
                ('farmer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plots', to='supply_chains.Farmer')),
                ('updater', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updater_farmerplot_objects', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created_on',),
                'abstract': False,
            },
        ),
        migrations.RunPython(initialize)
    ]
