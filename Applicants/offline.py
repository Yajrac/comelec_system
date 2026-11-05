"""Public, anonymous offline shells; never cache filled forms or staff pages."""
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.contrib.staticfiles.storage import staticfiles_storage
from django.contrib.staticfiles import finders
from django.conf import settings
from pathlib import Path
import hashlib
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from .eligibility import election_date
from .models import Barangay


def shell_context():
    return {'csrf_token': 'NOTPROVIDED', 'barangays': list(Barangay.objects.order_by('name')),
            'voter_election_date': election_date().isoformat()}


@require_GET
@never_cache
def connection_status(request):
    return JsonResponse({'online': True})


@require_GET
def saved_applications(request):
    return render(request, 'applicant/offline.html')


@require_GET
def service_worker(request):
    context = shell_context()
    version = '|'.join([staticfiles_storage.url('js/web-offline.js'),
                        staticfiles_storage.url('css/web-offline.css'), election_date().isoformat(),
                        render_to_string('applicant/home.html', context),
                        render_to_string('applicant/offline.html', context),
                        render_to_string('applicant/forms/new_registration.html', context)])
    if settings.DEBUG:
        for asset in ('js/web-offline.js', 'css/web-offline.css'):
            source = finders.find(asset)
            if source:
                version += str(Path(source).stat().st_mtime_ns)
    response = HttpResponse(render_to_string('offline/service-worker.js', {
        'offline_version': hashlib.sha256(version.encode()).hexdigest()[:16],
    }), content_type='application/javascript')
    response['Cache-Control'] = 'no-cache'
    response['Service-Worker-Allowed'] = '/'
    return response


@require_GET
def offline_shell(request, page):
    templates = {'home': 'applicant/home.html', 'registration': 'applicant/forms/new_registration.html', 'saved': 'applicant/offline.html'}
    context = shell_context()
    context['offline_page'] = page
    # No request/session context: only public fields and current lookup settings.
    response = HttpResponse(render_to_string(templates[page], context))
    response['Cache-Control'] = 'no-store'
    return response
