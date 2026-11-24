from django.urls import URLPattern, URLResolver, path

from marmotte.api import api

urlpatterns: list[URLPattern | URLResolver] = [
    path("api/", api.urls),
]
