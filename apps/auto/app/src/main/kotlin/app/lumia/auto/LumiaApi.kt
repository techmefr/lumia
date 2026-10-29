package app.lumia.auto

import org.json.JSONException
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

sealed interface SignInResult {
    data object Success : SignInResult
    data object BadCredentials : SignInResult
    data object SecondFactorRequired : SignInResult
    data object Failed : SignInResult
}

class UnauthorizedException : IOException("unauthorized")

class LumiaApi(private val store: SessionStore) {
    private class Response(val status: Int, val body: String)

    fun signIn(baseUrl: String, email: String, password: String): SignInResult {
        val payload = JSONObject().put("email", email).put("password", password).toString()
        val response = try {
            send("POST", "$baseUrl/auth/login", payload, null)
        } catch (error: IOException) {
            return SignInResult.Failed
        }
        return when {
            response.status == 200 -> {
                val tokens = try {
                    LumiaParsers.parseTokenPair(response.body)
                } catch (error: JSONException) {
                    return SignInResult.Failed
                }
                store.baseUrl = baseUrl
                store.save(tokens)
                SignInResult.Success
            }
            response.status == 401 && LumiaParsers.isSecondFactorRequired(response.body) ->
                SignInResult.SecondFactorRequired
            response.status == 401 -> SignInResult.BadCredentials
            else -> SignInResult.Failed
        }
    }

    fun playlists(): List<PlaylistSummary> =
        LumiaParsers.parsePlaylists(authorizedGet("/playlists"))

    fun playlist(id: String): PlaylistDetail =
        LumiaParsers.parsePlaylist(authorizedGet("/playlists/$id"))

    fun signOut() {
        val baseUrl = store.baseUrl
        val refreshToken = store.refreshToken
        if (baseUrl != null && refreshToken != null) {
            val payload = JSONObject().put("refresh_token", refreshToken).toString()
            try {
                send("POST", "$baseUrl/auth/logout", payload, null)
            } catch (error: IOException) {
                Unit
            }
        }
        store.clear()
    }

    @Synchronized
    fun validAccessToken(): String? {
        val current = store.accessToken
        val expiry = current?.let { LumiaParsers.tokenExpiryEpochSeconds(it) }
        val stillValid = expiry != null && expiry - System.currentTimeMillis() / 1000 > TOKEN_LEEWAY_SECONDS
        if (current != null && stillValid) return current
        return refresh()
    }

    private fun refresh(): String? {
        val baseUrl = store.baseUrl ?: return null
        val refreshToken = store.refreshToken ?: return null
        val payload = JSONObject().put("refresh_token", refreshToken).toString()
        val response = send("POST", "$baseUrl/auth/refresh", payload, null)
        if (response.status == 401) {
            store.clear()
            return null
        }
        if (response.status != 200) throw IOException("refresh status ${response.status}")
        val tokens = try {
            LumiaParsers.parseTokenPair(response.body)
        } catch (error: JSONException) {
            throw IOException("malformed refresh response", error)
        }
        store.save(tokens)
        return tokens.accessToken
    }

    private fun authorizedGet(path: String): String {
        val baseUrl = store.baseUrl ?: throw UnauthorizedException()
        val token = validAccessToken() ?: throw UnauthorizedException()
        val response = send("GET", "$baseUrl$path", null, token)
        if (response.status == 401) throw UnauthorizedException()
        if (response.status != 200) throw IOException("status ${response.status}")
        return response.body
    }

    private fun send(method: String, url: String, body: String?, token: String?): Response {
        val connection = URL(url).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = method
            connection.connectTimeout = TIMEOUT_MILLIS
            connection.readTimeout = TIMEOUT_MILLIS
            connection.setRequestProperty("accept", "application/json")
            if (token != null) connection.setRequestProperty("authorization", "Bearer $token")
            if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("content-type", "application/json")
                connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() } ?: ""
            return Response(status, text)
        } finally {
            connection.disconnect()
        }
    }

    private companion object {
        const val TIMEOUT_MILLIS = 15_000
        const val TOKEN_LEEWAY_SECONDS = 30L
    }
}
