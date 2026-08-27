from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),

    path(
        "dashboard/",
        include("dashboard.urls"),
    ),
]

# Product images are uploaded through the Django admin and stored under MEDIA_ROOT.
# This development-only route exposes opaque media URLs, never filesystem paths.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
