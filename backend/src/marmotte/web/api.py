"""HTTP API of Marmotte, mounted under ``/api/``."""

from django.http import HttpRequest
from ninja import NinjaAPI, Schema

from marmotte import __version__

api = NinjaAPI(title="Marmotte", version=__version__)


class HealthOut(Schema):
    status: str
    version: str


@api.get("/health", response=HealthOut)
def health(request: HttpRequest) -> HealthOut:
    """Tell that the web service is up, and which version runs."""
    return HealthOut(status="ok", version=__version__)
