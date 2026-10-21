from django.apps import AppConfig
from django.db.models.signals import post_migrate


class PlumeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plume"
    verbose_name = "MasomoPlus Plume"

    def ready(self):
        from .defauts import creer_valeurs_par_defaut

        post_migrate.connect(creer_valeurs_par_defaut, sender=self)
