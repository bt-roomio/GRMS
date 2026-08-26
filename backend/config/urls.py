from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from django_prometheus import exports as prometheus_exports

from main.metrics import update_device_metrics

from .yasg import urlpatterns as doc_path  # ty: ignore


def to_front_login(request):
    return redirect(f"{settings.FRONTEND_DOMAIN}/auth/login")


def to_front_signup(request):
    return redirect(f"{settings.FRONTEND_DOMAIN}/auth/login")


def metrics_view(request):
    update_device_metrics()
    return prometheus_exports.ExportToDjangoView(request)


urlpatterns = [
    path(
        "api/v1/",
        include(
            [
                *doc_path,
                path("users/", include(("users.urls", "users"), namespace="users")),
                path("main/", include(("main.urls", "main"), namespace="main")),
                path("shuttle/", include(("shuttle.urls", "shuttle"), namespace="shuttle")),
                path("access-manager/", include(("access_manager.urls", "access_manager"), namespace="access_manager")),
                path("services/", include(("services.urls", "services"), namespace="services")),
                path("admin/", include(("admin_panel.urls", "admin_panel"), namespace="admin_panel")),
                path("fleet/", include(("fleet.urls", "fleet"), namespace="fleet")),
            ]
        ),
    ),
    path("metrics", metrics_view, name="prometheus-django-metrics"),
    path("", include(("hoteza.urls", "hoteza"), namespace="hoteza-integration")),
    path("", include(("fleet.install_urls", "fleet_install"), namespace="fleet-install")),
    path("login/", to_front_login),
    path("signup/", to_front_signup),
    path("accounts/login/", to_front_login, name="account_login"),
    path("accounts/signup/", to_front_signup, name="account_signup"),
    path("accounts/", include("allauth.urls")),
]

if settings.DEBUG and not settings.TESTING:
    urlpatterns += [path("admin/", admin.site.urls)]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
