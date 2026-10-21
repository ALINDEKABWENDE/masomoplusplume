from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("comptes/", include("comptes.urls")),
    path("gestion/", include("gestion.urls")),
    path("messages/", include("messagerie.urls")),
    path("", include("plume.urls")),
]

# Les images de profil sont servies par Django en développement.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
