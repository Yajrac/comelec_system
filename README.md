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
| SMS integration | IPROG SMS API | Registration and application-status notifications |
| Fingerprint integration | Python, PySerial | Communication with the fingerprint scanner |
| Image processing | Pillow | Image handling |
| Deployment tools | Gunicorn, WhiteNoise | Serving the Django application and static files |

### Database Configuration

The current configuration in `web/settings.py` uses **SQLite** (`db.sqlite3`). A PostgreSQL configuration is present but commented out, and the Python dependencies include the PostgreSQL driver `psycopg`. MySQL is not the currently configured database.

### SMS Provider

The project currently integrates **IPROG SMS API**. Semaphore has been considered as an alternative but has not been integrated.

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


