# Pio Duran Signature (Android)

The app bundles its own signing interface and uses the existing VPS signature API.
The browser signing page remains available during Android testing.

## Build and test

1. Run `npm ci` in this folder after cloning.
2. Run `npx cap add android` once if the Android folder does not exist.
3. Run `npm run check`, then `npm run sync` after changing files in `www`.
4. Run `npm run android` to open Android Studio. Allow Gradle sync to finish.
5. Connect an Android device with USB debugging enabled and use Run, or generate
   a debug APK using Android Studio's Build menu.

Android Studio must have the SDK requested by the generated Gradle project.
Local SDK paths, build artifacts, and APKs are not committed.

## Signing

In the administrator biometrics page, click **Pair / replace signature app**.
Enter the 12-character code in the Android app within 5 minutes. Pair before
starting Capture Signature. The app remembers the device token across restarts.
Start Capture Signature for each desired sample; the paired app automatically
shows the applicant and sample. Verify the name, sign, and submit. After saving,
the app returns to waiting and receives the next request automatically.

Pairing is scoped to one officer account, not a browser tab. Use distinct officer
accounts for separate stations. Creating a new pairing code revokes the previously
paired device. Codes are single-use and stored hashed on the server; device tokens
are also hashed server-side. Disconnect device clears the token on the phone.
The latest request for an officer cancels their previous waiting requests.
QR scanning is not included. Internet is required for polling and submission.
Drawings stay in memory and are lost if the app closes before saving.

Deploy migration `Applicants.0032_signaturedevicepairing`, collectstatic, and reload
Gunicorn before testing this APK. The original web signing links still work.

CapacitorHttp is enabled to use native Android requests across the local WebView
and VPS origins without loosening backend CORS settings. Browser previews require
mocked API requests; validate real connectivity on Android. The HTML/CSS and drawing
logic are adapted from the web signing page; keep both copies aligned when fixing
shared drawing behavior.
