from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render
from django.utils.crypto import salted_hmac


class PageRateLimitMiddleware:
    """Short burst limit for page navigation; API/device polling is handled separately."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # The offline-sync connection check polls; a 429 would make queued forms look offline forever.
        exempt = (settings.STATIC_URL, settings.MEDIA_URL, "/api/", "/comelec/api/", "/offline/connection/")
        limit = settings.PAGE_RATE_LIMIT_REQUESTS
        if request.method not in {"GET", "HEAD"} or any(
                prefix and request.path.startswith(prefix) for prefix in exempt) or limit <= 0:
            return self.get_response(request)
        interval = settings.PAGE_RATE_LIMIT_SECONDS
        key = "page-rate:" + salted_hmac("page-rate", request.META.get("REMOTE_ADDR", "unknown")).hexdigest()
        # Atomic increments on shared production caches; fixed expiry is not extended by refreshes.
        cache.add(key, 0, timeout=interval)
        try:
            count = cache.incr(key)
        except ValueError:
            cache.add(key, 0, timeout=interval)
            count = cache.incr(key)
        if count <= limit:
            return self.get_response(request)
        response = render(request, "errors/429.html", {"retry_after": interval}, status=429)
        response["Retry-After"] = str(interval)
        response["Cache-Control"] = "no-store"
        return response
