from django.http import JsonResponse
from django.shortcuts import render


def page_not_found(request, exception=None):
    if request.path.startswith(("/api/", "/comelec/api/")):
        return JsonResponse({"success": False, "error": "Endpoint not found."}, status=404)
    admin_path = request.path == '/comelec' or request.path.startswith('/comelec/')
    is_admin = request.user.is_authenticated and request.user.is_superuser
    template = 'errors/404.html' if admin_path else 'errors/applicant_404.html'
    return render(request, template, {"is_admin": is_admin}, status=404)


class FriendlyNotFoundMiddleware:
    """Use the same 404 page during local development and production."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 404 and response.get("Content-Type", "").startswith("text/html"):
            return page_not_found(request)
        return response
