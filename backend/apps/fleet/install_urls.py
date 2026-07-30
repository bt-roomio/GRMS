from django.urls import path

from fleet.views.install import InstallScriptView

# Mounted at the site root so the one-liner stays short:
#   curl -fsSL "https://grms.example.com/install/marriott_42?t=..." | sudo bash
urlpatterns = [
    path("install/<str:code>", InstallScriptView.as_view(), name="install-script"),
    path("install/<str:code>/", InstallScriptView.as_view(), name="install-script-slash"),
]
