from .base import *

DEBUG = True
API_DOCS_ENABLED = True
# Kompyuterdagi Docker diski serverniki emas: ogohlantirish faqat production'da.
RESOURCE_CHECKS = env.bool("RESOURCE_CHECKS", default=False)

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
