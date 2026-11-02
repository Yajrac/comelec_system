# Mobile API connection

All mobile requests use `src/services/apiConfig.js`. Set `VITE_API_URL` in
`mobile/pio-duran-app/.env.local` (copy `.env.example` first):

```dotenv
VITE_API_URL=https://your-domain.example
```

Use your actual Django server origin without `/api`. The root Django `.env`
does not configure the mobile app. A physical phone cannot reach your laptop
or VPS through `localhost`; use the live HTTPS domain, or your laptop's LAN
address for local development.

After changing this setting, run `npm run build`. For Android, run
`npx cap sync android`, then rebuild and reinstall the APK. Changing the VPS
environment alone does not update an already installed app.

Check the server's `/api/registration-config/` and `/api/barangays/` endpoints
before testing submissions. Without a setting the app uses
`http://localhost:8000` for local development.

# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
