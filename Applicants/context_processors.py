from .eligibility import election_date


def election_settings(request):
    from .document_check import ai_enabled
    return {"voter_election_date": election_date().isoformat(), "document_ai_enabled": ai_enabled()}
