"""
URL configuration for birdy_config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# --- birdy_config/urls.py ---
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.views.static import serve
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('detections/', views.detections, name='detections'),
    path('statistics/', views.statistics, name='statistics'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]

# Media files (Videos, Photos) - direkt über Django ausliefern (kein Nginx)
from django.urls import re_path
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

