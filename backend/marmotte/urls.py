from django.urls import URLPattern
from django.urls import URLResolver
from django.urls import path

from marmotte.api import api

urlpatterns: list[URLPattern | URLResolver] = [
    path("api/", api.urls),
]
