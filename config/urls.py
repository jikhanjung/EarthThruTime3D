from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from core.views import healthz
from core.globe import globe, land_field, plate_file, source_map

urlpatterns = [
    path('', globe, name='home'),
    path('globe/maps/<slug:map_id>.jpg', source_map, name='globe-map'),
    path('globe/fields/<slug:map_id>.png', land_field, name='globe-field'),
    path('plates/<slug:model>/<slug:layer>.json', plate_file, name='plate-file'),
    path('about/', TemplateView.as_view(template_name='core/about.html'), name='about'),
    path('privacy/', TemplateView.as_view(template_name='core/privacy.html'), name='privacy'),
    path('contact/', TemplateView.as_view(template_name='core/contact.html'), name='contact'),
    path('healthz', healthz, name='healthz'),
    path('admin/', admin.site.urls),
]
