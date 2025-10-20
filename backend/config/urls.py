from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

from .yasg import urlpatterns as doc_path


def to_front_login(request):
    return redirect(f"{settings.FRONTEND_DOMAIN}/auth/login")


def to_front_signup(request):
    return redirect(f"{settings.FRONTEND_DOMAIN}/auth/login")


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
            ]
        ),
    ),
    path("", include(("hoteza.urls", "hoteza"), namespace="hoteza-integration")),
    path("", include("django_prometheus.urls")),
    path("login/", to_front_login),
    path("signup/", to_front_signup),
    path("accounts/login/", to_front_login, name="account_login"),
    path("accounts/signup/", to_front_signup, name="account_signup"),
    path("accounts/", include("allauth.urls")),
]

if settings.DEBUG:
    urlpatterns += [path("admin/", admin.site.urls)]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
