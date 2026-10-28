package app.lumia.auto

import android.os.Bundle
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.datasource.DefaultHttpDataSource
import androidx.media3.datasource.ResolvingDataSource
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import androidx.media3.session.LibraryResult
import androidx.media3.session.MediaLibraryService
import androidx.media3.session.MediaSession
import com.google.common.collect.ImmutableList
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture
import com.google.common.util.concurrent.ListeningExecutorService
import com.google.common.util.concurrent.MoreExecutors
import java.io.IOException
import java.util.concurrent.Callable
import java.util.concurrent.Executors

class LumiaLibraryService : MediaLibraryService() {
    private var librarySession: MediaLibrarySession? = null
    private val worker: ListeningExecutorService =
        MoreExecutors.listeningDecorator(Executors.newSingleThreadExecutor())

    override fun onCreate() {
        super.onCreate()
        val store = SessionStore(this)
        val api = LumiaApi(store)

        val dataSourceFactory = ResolvingDataSource.Factory(DefaultHttpDataSource.Factory()) { spec ->
            val token = api.validAccessToken()
            if (token == null) spec else spec.withAdditionalHeaders(mapOf("Authorization" to "Bearer $token"))
        }
        val player = ExoPlayer.Builder(this)
            .setMediaSourceFactory(DefaultMediaSourceFactory(dataSourceFactory))
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(C.USAGE_MEDIA)
                    .setContentType(C.AUDIO_CONTENT_TYPE_SPEECH)
                    .build(),
                true,
            )
            .setHandleAudioBecomingNoisy(true)
            .build()

        librarySession = MediaLibrarySession.Builder(this, player, LibraryCallback(store, api)).build()
    }

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaLibrarySession? =
        librarySession

    override fun onDestroy() {
        librarySession?.let {
            it.player.release()
            it.release()
        }
        librarySession = null
        worker.shutdown()
        super.onDestroy()
    }

    private inner class LibraryCallback(
        private val store: SessionStore,
        private val api: LumiaApi,
    ) : MediaLibrarySession.Callback {

        override fun onGetLibraryRoot(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            params: LibraryParams?,
        ): ListenableFuture<LibraryResult<MediaItem>> {
            val root = MediaItem.Builder()
                .setMediaId(MediaIds.ROOT)
                .setMediaMetadata(
                    MediaMetadata.Builder()
                        .setTitle(getString(R.string.library_root))
                        .setIsBrowsable(true)
                        .setIsPlayable(false)
                        .setMediaType(MediaMetadata.MEDIA_TYPE_FOLDER_MIXED)
                        .build(),
                )
                .build()
            return Futures.immediateFuture(LibraryResult.ofItem(root, params))
        }

        override fun onGetChildren(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            parentId: String,
            page: Int,
            pageSize: Int,
            params: LibraryParams?,
        ): ListenableFuture<LibraryResult<ImmutableList<MediaItem>>> = worker.submit(
            Callable {
                if (!store.isSignedIn()) return@Callable authExpired()
                try {
                    val items = if (parentId == MediaIds.ROOT) {
                        api.playlists().map { playlistItem(it) }
                    } else {
                        val playlistId = MediaIds.playlistOf(parentId) ?: return@Callable badValue()
                        val detail = api.playlist(playlistId)
                        detail.articles.map { articleItem(store, detail.id, it) }
                    }
                    LibraryResult.ofItemList(ImmutableList.copyOf(items), params)
                } catch (error: UnauthorizedException) {
                    authExpired()
                } catch (error: IOException) {
                    LibraryResult.ofError(LibraryResult.RESULT_ERROR_IO)
                }
            },
        )

        override fun onGetItem(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            mediaId: String,
        ): ListenableFuture<LibraryResult<MediaItem>> = worker.submit(
            Callable {
                if (!store.isSignedIn()) return@Callable LibraryResult.ofError<MediaItem>(
                    LibraryResult.RESULT_ERROR_SESSION_AUTHENTICATION_EXPIRED,
                )
                val playlistId = MediaIds.playlistOf(mediaId)
                val articleId = MediaIds.articleOf(mediaId)
                try {
                    val detail = api.playlist(playlistId ?: return@Callable LibraryResult.ofError<MediaItem>(
                        LibraryResult.RESULT_ERROR_BAD_VALUE,
                    ))
                    val article = detail.articles.firstOrNull { it.id == articleId }
                    if (article == null) {
                        LibraryResult.ofError<MediaItem>(LibraryResult.RESULT_ERROR_BAD_VALUE)
                    } else {
                        LibraryResult.ofItem(articleItem(store, detail.id, article), null)
                    }
                } catch (error: IOException) {
                    LibraryResult.ofError<MediaItem>(LibraryResult.RESULT_ERROR_IO)
                }
            },
        )

        override fun onSetMediaItems(
            mediaSession: MediaSession,
            controller: MediaSession.ControllerInfo,
            mediaItems: MutableList<MediaItem>,
            startIndex: Int,
            startPositionMs: Long,
        ): ListenableFuture<MediaSession.MediaItemsWithStartPosition> = worker.submit(
            Callable {
                val requested = mediaItems.firstOrNull()
                val playlistId = requested?.mediaId?.let { MediaIds.playlistOf(it) }
                val articleId = requested?.mediaId?.let { MediaIds.articleOf(it) }
                if (mediaItems.size != 1 || playlistId == null || articleId == null) {
                    return@Callable MediaSession.MediaItemsWithStartPosition(mediaItems, startIndex, startPositionMs)
                }
                val detail = api.playlist(playlistId)
                val queue = detail.articles.map { articleItem(store, detail.id, it) }
                val start = detail.articles.indexOfFirst { it.id == articleId }.coerceAtLeast(0)
                MediaSession.MediaItemsWithStartPosition(queue, start, C.TIME_UNSET)
            },
        )

        private fun playlistItem(playlist: PlaylistSummary): MediaItem = MediaItem.Builder()
            .setMediaId(MediaIds.playlist(playlist.id))
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(playlist.name)
                    .setIsBrowsable(true)
                    .setIsPlayable(false)
                    .setMediaType(MediaMetadata.MEDIA_TYPE_PLAYLIST)
                    .setExtras(Bundle().apply { putInt("item_count", playlist.itemCount) })
                    .build(),
            )
            .build()

        private fun articleItem(store: SessionStore, playlistId: String, article: Article): MediaItem =
            MediaItem.Builder()
                .setMediaId(MediaIds.article(playlistId, article.id))
                .setUri(LumiaParsers.audioUrl(store.baseUrl.orEmpty(), article.id))
                .setMediaMetadata(
                    MediaMetadata.Builder()
                        .setTitle(article.title)
                        .setArtist(article.sourceLabel)
                        .setIsBrowsable(false)
                        .setIsPlayable(true)
                        .setMediaType(MediaMetadata.MEDIA_TYPE_PODCAST_EPISODE)
                        .build(),
                )
                .build()

        private fun authExpired(): LibraryResult<ImmutableList<MediaItem>> =
            LibraryResult.ofError(LibraryResult.RESULT_ERROR_SESSION_AUTHENTICATION_EXPIRED)

        private fun badValue(): LibraryResult<ImmutableList<MediaItem>> =
            LibraryResult.ofError(LibraryResult.RESULT_ERROR_BAD_VALUE)
    }
}
