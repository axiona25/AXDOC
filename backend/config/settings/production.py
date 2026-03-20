"""
AXDOC — Production settings (FASE 14–15).
"""
from .base import *

DEBUG = False

# Dietro nginx con SSL (FASE 15)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# HSTS e cookie sicuri
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Redirect HTTP→HTTPS gestito da nginx, Django non fa redirect
SECURE_SSL_REDIRECT = False
