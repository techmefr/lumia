# Lumia for Android Auto

A native Kotlin app (Media3 MediaLibraryService, which also answers as a MediaBrowserService) that
exposes the reader playlists in the car. It talks to the same API as the other clients.

- Root lists the playlists, each playlist lists its articles; picking one queues the whole playlist
  from that article, so playback chains like the playFrom of the web playlist page.
- Audio is the server-generated reading, GET /articles/{id}/audio, the one the web player uses
  when a speech provider is configured. Without a provider the instance answers 503 and nothing
  plays; an on-device voice fallback is not implemented.
- Controls are the standard Auto ones: play/pause, next, previous.
- The phone-side screen signs in against the instance (address, email, password). The address is the
  instance origin; /api is appended when no path is given. Only https is accepted: cleartext is
  blocked by the network security config, and debug builds alone allow http to localhost, 127.0.0.1
  and 10.0.2.2. Accounts with a second factor are not supported yet.
- Tokens are stored encrypted with AES-GCM, under a non-exportable Android Keystore key. Signing out
  revokes the refresh token on the server (POST /auth/logout) before clearing the device.
- Only this app, Android Auto, the system UI and the assistant (or a controller the system trusts)
  may connect to the media session; any other package is rejected.
- Audio requests time out after 15 s to connect and 90 s to read. A 503 or 413 from the audio
  endpoint skips to the next article and shows a message.

## Build

Open apps/auto in Android Studio, or run ./gradlew assembleDebug with the Android SDK installed.
The Kotlin sources were written without a compiler at hand: run ./gradlew test assembleDebug first. To try it in a car, enable the Android Auto developer mode and allow
unknown sources.
