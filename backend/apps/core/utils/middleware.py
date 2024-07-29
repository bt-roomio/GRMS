from django.http import HttpResponseForbidden


class CheckForTenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        response = self.get_response(request)
        user = request.user
        if user.is_authenticated and not user.tenant:
            return HttpResponseForbidden("User does not have a tenant assigned.")

        return response
