"""Identification documents accepted for registration (COMELEC list), plus the PSA birth certificate.

Student IDs, the Community Tax Certificate (cedula) and PNP clearances are not accepted.
"""
VALID_ID_TYPES = [
    ("PHILSYS", "National ID (PhilSys)"),
    ("POSTAL", "Postal ID"),
    ("PWD", "PWD ID"),
    ("SENIOR", "Senior Citizen's ID"),
    ("DRIVERS_LICENSE", "LTO Driver's License / Student Permit"),
    ("NBI", "NBI Clearance"),
    ("PASSPORT", "Philippine Passport"),
    ("SSS_GSIS_UMID", "SSS / GSIS / UMID"),
    ("IBP", "IBP ID"),
    ("PRC", "PRC License"),
    ("NCIP", "NCIP Certificate of Confirmation"),
    ("BARANGAY", "Barangay ID / Certification with photo"),
    ("PSA_BIRTH_CERTIFICATE", "PSA Birth Certificate"),
    ("OTHER_GOVERNMENT", "Other government-issued ID"),
]
VALID_ID_CODES = {code for code, _ in VALID_ID_TYPES}
NOT_ACCEPTED_NOTE = "Not accepted: Student ID, Cedula (Community Tax Certificate) and PNP clearance."
