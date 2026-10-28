# Lumia for Android Auto

A native Kotlin app (Media3 MediaLibraryService, which also answers as a MediaBrowserService) that
exposes the reader playlists in the car. It talks to the same API as the other clients.

- Root lists the playlists, each playlist lists its articles; picking one queues the whole playlist
  from that article, so playback chains like the playFrom of the web playlist page.
- Audio is the server-generated reading, GET /articles/{id}/audio, the one the web player uses
  when a speech provider is configured. Without a provider the instance answers 503 and nothing
  plays; an on-device voice fallback is not implemented.
- Controls are the standard Auto ones: play/pause, next, previous.
- The phone-side screen signs in against the instance (API address, email, password). Accounts with
  a second factor are not supported yet.

## Build

Open apps/auto in Android Studio (it creates the Gradle wrapper), or run gradle assembleDebug with
the Android SDK installed. To try it in a car, enable the Android Auto developer mode and allow
unknown sources.
