package app.lumia.auto

import android.content.Context

class SessionStore(context: Context) {
    private val preferences = context.getSharedPreferences("lumia-auto", Context.MODE_PRIVATE)

    var baseUrl: String?
        get() = preferences.getString("base_url", null)
        set(value) = preferences.edit().putString("base_url", value).apply()

    var accessToken: String?
        get() = preferences.getString("access_token", null)
        set(value) = preferences.edit().putString("access_token", value).apply()

    var refreshToken: String?
        get() = preferences.getString("refresh_token", null)
        set(value) = preferences.edit().putString("refresh_token", value).apply()

    fun isSignedIn(): Boolean = baseUrl != null && refreshToken != null

    fun save(tokens: TokenPair) {
        preferences.edit()
            .putString("access_token", tokens.accessToken)
            .putString("refresh_token", tokens.refreshToken)
            .apply()
    }

    fun clear() {
        preferences.edit().clear().apply()
    }
}
