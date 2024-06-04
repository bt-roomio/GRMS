from drf_yasg import openapi

GeneralSettingsSwagger = {
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
}
