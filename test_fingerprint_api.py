
import os
import requests

# Replace with your actual Render domain.
BASE_URL = "https://pio-duran-online-registration.onrender.com/"

# Use an existing temporary test applicant.
APPLICANT_ID = 123

TOKEN = os.environ["FINGERPRINT_DEVICE_TOKEN"]

url = (
    f"{BASE_URL}/api/device/applicants/"
    f"{APPLICANT_ID}/fingerprint/"
)

# Test payload only — these are NOT real biometric data.
dummy_image = bytes(36864)
dummy_template = bytes(256)

response = requests.post(
    url,
    headers={"X-Device-Token": TOKEN},
    data={"finger": "left"},
    files={
        "fingerprint_image": (
            "test-image.bin",
            dummy_image,
            "application/octet-stream",
        ),
        "fingerprint_template": (
            "test-template.bin",
            dummy_template,
            "application/octet-stream",
        ),
    },
    timeout=60,
)

print("HTTP status:", response.status_code)
print("Response:", response.text)
