package app.lumia.auto

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Base64

class LumiaParsersTest {
    @Test
    fun normalizeKeepsOriginAndPathWithoutTrailingSlash() {
        assertEquals("https://lumia.example.com/api", LumiaParsers.normalizeBaseUrl(" https://lumia.example.com/api// "))
        assertEquals("http://192.168.1.10:8000", LumiaParsers.normalizeBaseUrl("http://192.168.1.10:8000"))
    }

    @Test
    fun normalizeRejectsNonHttpAndGarbage() {
        assertNull(LumiaParsers.normalizeBaseUrl(""))
        assertNull(LumiaParsers.normalizeBaseUrl("lumia.example.com"))
        assertNull(LumiaParsers.normalizeBaseUrl("ftp://lumia.example.com"))
    }

    @Test
    fun audioUrlPointsAtTheArticleAudioEndpoint() {
        assertEquals("https://x/api/articles/42/audio", LumiaParsers.audioUrl("https://x/api", "42"))
    }

    @Test
    fun parsesAPlaylistInItsOrder() {
        val body = """{"id":"p1","name":"Commute","articles":[
            {"id":"a1","title":"First","source_label":"Blog"},
            {"id":"a2","title":"Second","source_label":"News"}]}"""
        val playlist = LumiaParsers.parsePlaylist(body)
        assertEquals("Commute", playlist.name)
        assertEquals(listOf("a1", "a2"), playlist.articles.map { it.id })
        assertEquals("News", playlist.articles[1].sourceLabel)
    }

    @Test
    fun parsesPlaylistSummaries() {
        val playlists = LumiaParsers.parsePlaylists("""[{"id":"p1","name":"A","item_count":3}]""")
        assertEquals(PlaylistSummary("p1", "A", 3), playlists.single())
    }

    @Test
    fun readsTheSecondFactorChallenge() {
        assertTrue(LumiaParsers.isSecondFactorRequired("""{"detail":"totp_required"}"""))
        assertFalse(LumiaParsers.isSecondFactorRequired("""{"detail":"invalid_credentials"}"""))
        assertFalse(LumiaParsers.isSecondFactorRequired("not json"))
    }

    @Test
    fun readsTheExpiryOfAnAccessToken() {
        val payload = Base64.getUrlEncoder().withoutPadding().encodeToString("""{"exp":1700000000}""".toByteArray())
        assertEquals(1700000000L, LumiaParsers.tokenExpiryEpochSeconds("h.$payload.s"))
        assertNull(LumiaParsers.tokenExpiryEpochSeconds("opaque"))
    }

    @Test
    fun mediaIdsRoundTrip() {
        val id = MediaIds.article("p1", "a2")
        assertEquals("p1", MediaIds.playlistOf(id))
        assertEquals("a2", MediaIds.articleOf(id))
        assertEquals("p1", MediaIds.playlistOf(MediaIds.playlist("p1")))
        assertNull(MediaIds.articleOf(MediaIds.playlist("p1")))
        assertNull(MediaIds.playlistOf(MediaIds.ROOT))
    }

    @Test
    fun appendsTheApiPathOnlyWhenTheInstanceHasNone() {
        assertEquals("https://lumia.example.com/api", LumiaParsers.withApiPath("https://lumia.example.com"))
        assertEquals("https://x/custom", LumiaParsers.withApiPath("https://x/custom"))
        assertEquals("http://10.0.2.2:8000/api", LumiaParsers.withApiPath("http://10.0.2.2:8000"))
    }

    @Test
    fun refusesCleartextExceptForLocalDevelopmentOnDebugBuilds() {
        assertTrue(LumiaParsers.isAcceptedInstance("https://lumia.example.com/api", false))
        assertFalse(LumiaParsers.isAcceptedInstance("http://lumia.example.com/api", false))
        assertFalse(LumiaParsers.isAcceptedInstance("http://192.168.1.10:8000", true))
        assertFalse(LumiaParsers.isAcceptedInstance("http://10.0.2.2:8000", false))
        assertTrue(LumiaParsers.isAcceptedInstance("http://10.0.2.2:8000", true))
        assertTrue(LumiaParsers.isAcceptedInstance("http://localhost:8000", true))
    }

    @Test
    fun onlyKnownControllersMayConnect() {
        assertTrue(ControllerPolicy.isAllowed("app.lumia.auto", "app.lumia.auto", false))
        assertTrue(ControllerPolicy.isAllowed("com.google.android.projection.gearhead", "app.lumia.auto", false))
        assertTrue(ControllerPolicy.isAllowed("com.example.unknown", "app.lumia.auto", true))
        assertFalse(ControllerPolicy.isAllowed("com.example.unknown", "app.lumia.auto", false))
    }
}
