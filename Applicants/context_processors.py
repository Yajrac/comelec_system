from .eligibility import election_date


def election_settings(request):
    from .document_check import ai_enabled
    from .face_match import enabled as face_match_enabled
    from .id_types import NOT_ACCEPTED_NOTE, VALID_ID_TYPES
    return {"voter_election_date": election_date().isoformat(), "document_ai_enabled": ai_enabled(),
            "valid_id_types": VALID_ID_TYPES, "valid_id_note": NOT_ACCEPTED_NOTE,
            "face_match_enabled": face_match_enabled()}
