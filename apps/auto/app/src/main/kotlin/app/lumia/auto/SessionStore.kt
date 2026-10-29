package app.lumia.auto

import android.content.Context

class SessionStore(context: Context, private val cipher: TokenCipher = TokenCipher()) {
    private val preferences = context.getSharedPreferences("lumia-auto", Context.MODE_PRIVATE)

    init {
        if (preferences.contains(LEGACY_ACCESS) || preferences.contains(LEGACY_REFRESH)) {
            preferences.edit().remove(LEGACY_ACCESS).remove(LEGACY_REFRESH).apply()
        }
    }

    var baseUrl: String?
        get() = preferences.getString("base_url", null)
        set(value) = preferences.edit().putString("base_url", value).apply()

    val accessToken: String?
        get() = readSecret(ACCESS_KEY)

    val refreshToken: String?
        get() = readSecret(REFRESH_KEY)

    fun isSignedIn(): Boolean = baseUrl != null && refreshToken != null

    fun save(tokens: TokenPair) {
        preferences.edit()
            .putString(ACCESS_KEY, cipher.encrypt(tokens.accessToken))
            .putString(REFRESH_KEY, cipher.encrypt(tokens.refreshToken))
            .apply()
    }

    fun clear() {
        preferences.edit().clear().apply()
    }

    private fun readSecret(key: String): String? {
        val stored = preferences.getString(key, null) ?: return null
        return cipher.decrypt(stored)
    }

    private companion object {
        const val ACCESS_KEY = "access_token_enc"
        const val REFRESH_KEY = "refresh_token_enc"
        const val LEGACY_ACCESS = "access_token"
        const val LEGACY_REFRESH = "refresh_token"
    }
}
