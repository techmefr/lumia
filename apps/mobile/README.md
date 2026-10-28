# Lumia mobile

The web app (apps/web) wrapped with Capacitor, for Android and iOS. The UI is not duplicated: the
shell serves the static build of apps/web.

## Build

    pnpm --filter mobile android
    pnpm --filter mobile ios

Both build apps/web in mobile mode (its CSP then allows requests to any http(s) instance), sync the
native projects and open Android Studio or Xcode. Android needs the Android SDK, iOS needs macOS and
Xcode.

## Instance

The login screen shows an instance field in the native app. The address is kept on the device and
overrides VITE_API_BASE_URL. The API must list https://localhost (Android) and capacitor://localhost
(iOS) in CORS_ALLOWED_ORIGINS; the shipped compose file already does.

## Notifications

Alerts use the local notifications plugin, driven by the same unread-count poll as the web app, so
they fire while the app is running. Delivery while the app is closed needs server-side push, which
the backend does not provide yet.
