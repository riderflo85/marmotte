from django.http import HttpRequest
from ninja import Router

from marmotte.__version__ import __version__
from marmotte.base.schemas import HealthOut

router = Router(tags=["base"])


@router.get("/health", response=HealthOut)
def health(request: HttpRequest) -> HealthOut:
    """Tell that the web service is up, and which version runs."""
    return HealthOut(status="ok", version=__version__)
