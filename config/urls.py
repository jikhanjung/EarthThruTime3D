from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from core.views import healthz

urlpatterns = [
    path('', TemplateView.as_view(template_name='core/home.html'), name='home'),
    path('about/', TemplateView.as_view(template_name='core/about.html'), name='about'),
    path('privacy/', TemplateView.as_view(template_name='core/privacy.html'), name='privacy'),
    path('contact/', TemplateView.as_view(template_name='core/contact.html'), name='contact'),
    path('healthz', healthz, name='healthz'),
    path('admin/', admin.site.urls),
]
