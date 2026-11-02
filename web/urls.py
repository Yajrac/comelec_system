"""
URL configuration for web project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.contrib import admin
from core.views import admin_login
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.clickjacking import xframe_options_sameorigin

urlpatterns = [
    path('developer/login/', admin_login),
    path('developer/', admin.site.urls),
    path('comelec/', include('core.urls')),
    path('', include('Applicants.urls')),
    path('api/', include('api.urls')),
    
]

if settings.DEBUG:
    media_patterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    for media_pattern in media_patterns:
        # Allow document previews within this site while keeping other views protected.
        media_pattern.callback = xframe_options_sameorigin(media_pattern.callback)
    urlpatterns += media_patterns
handler404 = "core.error_pages.page_not_found"
