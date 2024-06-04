from drf_yasg import openapi
from main.serializers.alarm_settings import AlarmSettingsSerializer

AlarmSettingsSwagger = {
	400: openapi.Response(
		description="Bad request",
		examples={
			"application/json": {
				"detail": [
					"Authentication credentials were not provided.",
					"Given token not valid for any token type",
				]
			}
		},
	),
	200: openapi.Response(
		description="Alarm settings",
		schema=AlarmSettingsSerializer,
	),
}
