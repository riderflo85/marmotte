from django.urls import URLPattern, URLResolver, path

from marmotte.web.api import api

urlpatterns: list[URLPattern | URLResolver] = [
    path("api/", api.urls),
]
