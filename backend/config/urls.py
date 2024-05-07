from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from .yasg import urlpatterns as doc_path

urlpatterns = [
    path('api/v1/', include([
        *doc_path,
        path('users/', include(('users.urls', 'users'), namespace='users')),
        path('main/', include(('main.urls', 'main'), namespace='main'))
    ])),
]

if settings.DEBUG:
    urlpatterns += [
        path('admin/', admin.site.urls)
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
