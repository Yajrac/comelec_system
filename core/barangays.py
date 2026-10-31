"""Pio Duran barangays from the Philippine Statistics Authority PSGC.
Source: https://psa.gov.ph/classification/psgc/barangays/0500513000
Retrieved 2026-10-30. Update this local catalog when PSA changes the list.
"""
PIO_DURAN_BARANGAYS = tuple(sorted([
    "Agol", "Alabangpuro", "Basicao Coastal", "Basicao Interior", "Banawan",
    "Binodegahan", "Buenavista", "Buyo", "Caratagan", "Cuyaoyao", "Flores",
    "Lawinon", "Macasitas", "Malapay", "Malidong", "Mamlad", "Marigondon",
    "Matanglad", "Nablangbulod", "Oringon", "Palapas", "Panganiran",
    "Barangay I", "Barangay II", "Barangay III", "Barangay IV", "Barangay V",
    "Rawis", "Salvacion", "Santo Cristo", "Sukip", "Tibabo", "La Medalla",
]))


def normalize_barangay_name(value):
    return " ".join(value.split()).casefold()


def canonical_barangay_name(value):
    normalized = normalize_barangay_name(value)
    return next((name for name in PIO_DURAN_BARANGAYS
                 if normalize_barangay_name(name) == normalized), None)
