"""HTTP API of Marmotte: gathers the router of each module."""

from ninja import NinjaAPI

from marmotte.__version__ import __version__
from marmotte.base.api_urls import router as base_router

api = NinjaAPI(title="Marmotte", version=__version__)
api.add_router("", base_router)
