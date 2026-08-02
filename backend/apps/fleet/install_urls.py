from django.urls import path

from fleet.views.install import InstallScriptView

urlpatterns = [
    path("install/<str:code>", InstallScriptView.as_view(), name="install-script"),
    path("install/<str:code>/", InstallScriptView.as_view(), name="install-script-slash"),
]
