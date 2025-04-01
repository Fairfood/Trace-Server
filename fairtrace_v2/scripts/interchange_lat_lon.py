"""
The latitude and longitude of plots of farmers uploaded on date 
'2024-10-24', '2024-10-23 via bulk upload was incorrect. ie, latitude and 
longitude of type 'Point' were interchanged 
"""


from v2.supply_chains.models.profile import Farmer


farmers = Farmer.objects.filter(
    created_on__date__in=['2024-10-24', '2024-10-23']
).prefetch_related('plots')

for farmer in farmers:
    for plot in farmer.plots.all():
        geo_json = plot.geo_json
        if 'geometry' in geo_json:
            if geo_json['geometry']['type'] == 'Point':
                lat = geo_json['geometry']['coordinates'][1]
                lon = geo_json['geometry']['coordinates'][0]
                geo_json['geometry']['coordinates'] = [lat, lon]
        plot.geo_json = geo_json
        plot.save()
