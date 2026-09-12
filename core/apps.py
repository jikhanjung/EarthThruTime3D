from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class CoreAdminConfig(AdminConfig):
    default_site = 'core.admin_site.SuperuserAdminSite'


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
