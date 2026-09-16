from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from core.views import healthz, language
from core.access import gate
from core.mantle import mantle, mantle_asset
from core.crust import crust_asset
from core.collision import collision, collision_data
from core.globe import ice_mask, ice_low, river_field, river_ice_field, river_low_field, temperature_map, coastline_file, globe, land_field, plate_file, source_map

urlpatterns = [
    path('collision/', collision, name='collision'),
    path('collision/data/<slug:version>.json', collision_data, name='collision-data'),
    path('mantle/', mantle, name='mantle'),
    path('mantle/assets/<str:filename>', mantle_asset, name='mantle-asset'),
    path('crust/assets/<str:filename>', crust_asset, name='crust-asset'),
    path('', globe, name='home'),
    path('globe/maps/<slug:map_id>.jpg', source_map, name='globe-map'),
    path('globe/fields/<slug:map_id>.png', land_field, name='globe-field'),
    path('globe/temps/<slug:map_id>.png', temperature_map, name='globe-temperature'),
    path('globe/ice/<slug:map_id>.png', ice_mask, name='globe-ice'),
    path('globe/ice-low/<slug:map_id>/<int:age>.png', ice_low, name='globe-ice-low'),
    path('globe/rivers/<slug:map_id>.png', river_field, name='globe-rivers'),
    path('globe/rivers-low/<slug:map_id>.png', river_low_field, name='globe-rivers-low'),
    path('globe/rivers-ice/<slug:map_id>/<int:years>.png', river_ice_field, name='globe-rivers-ice'),
    path('globe/coastlines/<int:age>.json', coastline_file, name='globe-coastline'),
    path('plates/<slug:model>/<slug:layer>.json', plate_file, name='plate-file'),
    path('access/', gate, name='access-gate'),
    path('about/', TemplateView.as_view(template_name='core/about.html'), name='about'),
    path('privacy/', TemplateView.as_view(template_name='core/privacy.html'), name='privacy'),
    path('contact/', TemplateView.as_view(template_name='core/contact.html'), name='contact'),
    path('healthz', healthz, name='healthz'),
    path('lang/<slug:code>/', language, name='language'),
    path('admin/', admin.site.urls),
]
