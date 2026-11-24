"""Routes of the base module, mounted under /api/ by marmotte/api.py."""

from ninja import Router

from marmotte.base.views import health_router

router = Router()
router.add_router("", health_router)
