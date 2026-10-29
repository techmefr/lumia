package app.lumia.auto

import org.json.JSONObject
import java.net.URI
import java.util.Base64

data class TokenPair(val accessToken: String, val refreshToken: String)

data class PlaylistSummary(val id: String, val name: String, val itemCount: Int)

data class Article(val id: String, val title: String, val sourceLabel: String)

data class PlaylistDetail(val id: String, val name: String, val articles: List<Article>)

object LumiaParsers {
    private val LOCAL_DEVELOPMENT_HOSTS = setOf("localhost", "127.0.0.1", "10.0.2.2")

    fun normalizeBaseUrl(raw: String): String? {
        val trimmed = raw.trim()
        if (trimmed.isEmpty()) return null
        val uri = try {
            URI(trimmed)
        } catch (error: Exception) {
            return null
        }
        val scheme = uri.scheme?.lowercase()
        if (scheme != "http" && scheme != "https") return null
        val host = uri.host ?: return null
        val port = if (uri.port == -1) "" else ":${uri.port}"
        val path = (uri.path ?: "").trimEnd('/')
        return "$scheme://$host$port$path"
    }

    fun withApiPath(baseUrl: String): String {
        val path = URI(baseUrl).path ?: ""
        return if (path.isEmpty()) "$baseUrl/api" else baseUrl
    }

    fun isCleartext(baseUrl: String): Boolean = baseUrl.startsWith("http://", ignoreCase = true)

    fun isLocalDevelopmentHost(baseUrl: String): Boolean {
        val host = try {
            URI(baseUrl).host
        } catch (error: Exception) {
            null
        }
        return host in LOCAL_DEVELOPMENT_HOSTS
    }

    fun isAcceptedInstance(baseUrl: String, debuggable: Boolean): Boolean =
        !isCleartext(baseUrl) || (debuggable && isLocalDevelopmentHost(baseUrl))

    fun audioUrl(baseUrl: String, articleId: String): String = "$baseUrl/articles/$articleId/audio"

    fun parseTokenPair(body: String): TokenPair {
        val json = JSONObject(body)
        return TokenPair(json.getString("access_token"), json.getString("refresh_token"))
    }

    fun parsePlaylists(body: String): List<PlaylistSummary> {
        val array = org.json.JSONArray(body)
        return (0 until array.length()).map { index ->
            val item = array.getJSONObject(index)
            PlaylistSummary(item.getString("id"), item.getString("name"), item.optInt("item_count", 0))
        }
    }

    fun parsePlaylist(body: String): PlaylistDetail {
        val json = JSONObject(body)
        val articles = json.getJSONArray("articles")
        return PlaylistDetail(
            json.getString("id"),
            json.getString("name"),
            (0 until articles.length()).map { index ->
                val item = articles.getJSONObject(index)
                Article(item.getString("id"), item.getString("title"), item.optString("source_label", ""))
            },
        )
    }

    fun isSecondFactorRequired(body: String): Boolean = try {
        JSONObject(body).optString("detail") == "totp_required"
    } catch (error: Exception) {
        false
    }

    fun tokenExpiryEpochSeconds(accessToken: String): Long? {
        val payload = accessToken.split('.').getOrNull(1) ?: return null
        return try {
            val decoded = Base64.getUrlDecoder().decode(payload)
            JSONObject(String(decoded, Charsets.UTF_8)).getLong("exp")
        } catch (error: Exception) {
            null
        }
    }
}
