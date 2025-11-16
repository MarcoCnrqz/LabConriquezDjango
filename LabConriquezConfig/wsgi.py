"""
WSGI config for LabConriquez project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""
# wsgi es un apartado que permite desplgegar la aplicacin en un servidor web
# En este caso se usa el servidor de desarrollo de Django

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LabConriquez.settings')

application = get_wsgi_application()
