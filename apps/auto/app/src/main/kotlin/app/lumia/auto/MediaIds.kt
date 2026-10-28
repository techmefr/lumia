package app.lumia.auto

object MediaIds {
    const val ROOT = "root"

    private const val PLAYLIST_PREFIX = "playlist:"
    private const val ARTICLE_SEPARATOR = "/article:"

    fun playlist(playlistId: String): String = "$PLAYLIST_PREFIX$playlistId"

    fun article(playlistId: String, articleId: String): String =
        "${playlist(playlistId)}$ARTICLE_SEPARATOR$articleId"

    fun playlistOf(mediaId: String): String? {
        if (!mediaId.startsWith(PLAYLIST_PREFIX)) return null
        return mediaId.removePrefix(PLAYLIST_PREFIX).substringBefore(ARTICLE_SEPARATOR).ifEmpty { null }
    }

    fun articleOf(mediaId: String): String? {
        if (!mediaId.contains(ARTICLE_SEPARATOR)) return null
        return mediaId.substringAfter(ARTICLE_SEPARATOR).ifEmpty { null }
    }
}
