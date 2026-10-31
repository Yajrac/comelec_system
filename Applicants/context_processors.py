from .eligibility import election_date


def election_settings(request):
    return {"voter_election_date": election_date().isoformat()}
