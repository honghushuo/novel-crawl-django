"""
WSGI config for 基于多源小说站点爬虫的阅读平台研发 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', '基于多源小说站点爬虫的阅读平台研发.settings')

application = get_wsgi_application()
