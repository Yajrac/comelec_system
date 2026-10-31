# Online Registration for Local in Pio Duran, Albay

A web and Android application for local voter-registration services, with local data storage and synchronization, SMS notifications, and fingerprint scanner integration.

## Technology Stack

| Component | Technology | Purpose |
| --- | --- | --- |
| Backend | Python, Django 5.2 | Application logic, registration workflows, and administration |
| REST API | Django REST Framework | Communication between the mobile application and backend |
| Web frontend | HTML, CSS, JavaScript, Django Templates | Web pages, forms, and server-rendered content |
| Web UI | Bootstrap 5.3, Bootstrap Icons | Responsive layouts and interface components |
| Mobile frontend | React 19, React Router | Mobile screens and navigation |
| Android integration | Capacitor 8 | Packaging the React application as an Android app |
| Frontend build tool | Vite 8 | Mobile frontend development and production builds |
| Backend database | SQLite | Current Django database for application records |
| Mobile storage | Capacitor Community SQLite, Capacitor Preferences | Local database and application preferences |
| Mobile connectivity | Capacitor Network | Network connectivity detection |
| HTTP communication | Axios, Python Requests | API requests from the mobile app and backend integrations |
| SMS integration | iProg SMS API | Registration and application-status notifications |
| Fingerprint integration | Python, PySerial | Communication with the fingerprint scanner |
| Image processing | Pillow | Image handling |
| Deployment tools | Gunicorn, WhiteNoise | Serving the Django application and static files |

### Database Configuration

The current configuration in `web/settings.py` uses **SQLite** (`db.sqlite3`). A PostgreSQL configuration is present but commented out, and the Python dependencies include the PostgreSQL driver `psycopg`. MySQL is not the currently configured database.

### SMS Provider

The backend currently uses **iProg SMS API** for application-status notifications while the Semaphore sender is pending approval.

Set `IPROG_SMS_API_TOKEN` in the server's `.env` (never commit real tokens), then restart Django. Existing Semaphore settings and its helper remain available for a later switch, but application notifications currently call iProg only. No automatic provider fallback or retries are used to avoid duplicate messages.

The API token stays on the Django server. Messages use `POST https://www.iprogsms.com/api/v1/sms_messages` with JSON fields `api_token`, `phone_number`, and `message`. API acceptance means queued, not confirmed handset delivery. See the [iProg integration guide](https://www.iprogsms.com/blog/building-sms-notifications-into-your-app-developers-guide).

### Hosting

Ubuntu hosting on Hostinger and a domain are listed as deployment requirements. This does not confirm the current live hosting environment.

## Hardware and Biometric Capture

### Fingerprint Scanner

The fingerprint integration in `core/fingerprint/scanner.py` is designed for an **AS608 fingerprint sensor** connected through an **ESP8266 microcontroller**. The computer communicates with the ESP8266 through a serial connection using Python's PySerial library.

- Preferred serial port: `COM7`, with serial-port discovery logic.
- Computer-to-ESP8266 baud rate: `115200`.
- Fingerprint image dimensions: `256 x 288` pixels.

These details describe the hardware expected by the code; the physically installed device has not been verified.

### Electronic Signature

The backend supports signature-capture sessions and stores the applicant's electronic signature as a **PNG image**. The session handling is implemented in `core/views.py`, and the signature file field is defined in `Applicants/models.py`.

The signature device's brand and model are not identified in the reviewed code. Confirm the actual input device with the project implementer; compatibility with a particular signature pad or touchscreen has not been verified.

## Screenshots

<img width="1896" height="912" alt="Screenshot 2026-09-14 121912" src="https://github.com/user-attachments/assets/fd255bc2-980f-4f14-b1b2-a44a06303c05" />

<img width="1895" height="912" alt="Screenshot 2026-09-14 122009" src="https://github.com/user-attachments/assets/0ad4675c-f633-4159-8b59-73b720cb9c37" />

<img width="1275" height="833" alt="Screenshot 2026-09-14 122136" src="https://github.com/user-attachments/assets/ce005677-6a0e-4aab-bba6-011e9667ba06" />




## Three applicant signature samples

The administrator biometrics screen captures **Signature 1, 2, and 3** separately, with individual previews and retakes. The original `applicant_signature` is preserved as sample 1; samples 2 and 3 use separate file fields. Verification requires both fingerprint images and all three signature files. Fingerprint templates remain optional.

Migration `0021` adds these fields without deleting existing signatures. Existing biometric completion flags are reset to pending because the newly required samples are not present yet. A local database/signature backup was created under `.local-backups/` before the upgrade; do not commit backups.

The signing device continues to poll `/comelec/api/signature/waiting/` and post a JSON body with `session_id` and the PNG data URL `signature` to `/comelec/api/signature/complete/`. The server session determines the target slot; devices can ignore the added `signature_slot` response field. Administrator session creation accepts `signature_slot` (1, 2, or 3), defaulting to 1 for older callers. Start one capture at a time. Retakes replace only their selected slot and preserve previous physical signature files.

Run simulated device uploads with:

```powershell
python manage.py test core.test_signatures
```

These tests use isolated test records and in-memory image storage. They do not submit actual applicant signatures or contact hardware. Actual signing-device compatibility must still be checked on the physical device.

### Client admin handover and login limits

The custom administrator login locks a username for 15 minutes after 5 failed attempts. A separate IP bucket locks after 20 failures in 15 minutes. Limits are stored in the database and use REMOTE_ADDR; forwarded headers are not trusted. Behind a reverse proxy, configure trusted client IP handling before relying on per-IP differentiation.

Prepare a client account with `python manage.py prepare_admin_handover clientadmin`. The command securely prompts for a temporary password (not echoed), creates a new superuser or resets the named existing superuser, and requires replacement before access to the workspace. Existing accounts are not flagged automatically. Do not run this command on your working account unless you intend to reset it. Django password validators and current-password verification apply to the replacement. All authenticated requests by a flagged admin are redirected until the password is changed, except change-password and sign-out.

### Page refresh burst protection

Browser GET/HEAD requests are limited to 30 requests per 10 seconds per REMOTE_ADDR, returning a friendly HTTP 429 with Retry-After. Static/media files, API/device routes, and POST submissions are excluded from this page limiter; login POSTs retain their own database-backed attempt limits. Limits use Django cache. The default local-memory cache is per process and resets on restart; configure a shared cache and trusted proxy IP handling plus proxy-level limits for multi-worker production hosting. This is basic application throttling, not DDoS protection.

### Registration trends and demographics

Dashboard shows the current year's monthly submission totals and applicant age/sex/PWD charts. Reports supports monthly trends for a selected year or yearly trends for all years; missing periods have zero counts. Trend change is the absolute count difference from the preceding displayed period. Trends count new applications plus each service request on its submission date.

Demographics count each Applicant once, restricted by the year of their original registration, across all statuses. Age uses birthdate as of the report generation date, not stored age or age at submission; these are current cohort demographics, not historical demographic snapshots. Each age/sex/PWD category totals the same unique applicant denominator; do not add the categories together. Missing or unexpected values are shown as Unknown. All reports support year selection, full-data PDF download and printable pagination.


Birthdate and election age checks use `VOTER_ELECTION_DATE` (default `2028-11-13`, BSKE).
Set this environment variable to the official election date for the registration cycle.
The form displays age on that date: 15?17 meets the SK age requirement, 18?30 meets
both regular-voter and SK age requirements, and 31+ meets the regular-voter age
requirement. This checks age only; it does not determine registration-period,
residency, citizenship, or final COMELEC approval. Current age remains calculated
from birthdate separately. Web and API submissions enforce the same minimum age.
