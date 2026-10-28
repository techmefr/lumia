package app.lumia.auto

import android.app.Activity
import android.os.Bundle
import android.text.InputType
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import java.util.concurrent.Executors

class SettingsActivity : Activity() {
    private val worker = Executors.newSingleThreadExecutor()
    private lateinit var store: SessionStore
    private lateinit var api: LumiaApi
    private lateinit var status: TextView
    private lateinit var instance: EditText
    private lateinit var email: EditText
    private lateinit var password: EditText
    private lateinit var action: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        store = SessionStore(this)
        api = LumiaApi(store)

        val padding = (resources.displayMetrics.density * PADDING_DP).toInt()
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
        }
        status = TextView(this)
        instance = field(R.string.settings_instance, InputType.TYPE_TEXT_VARIATION_URI)
        instance.hint = getString(R.string.settings_instance_hint)
        email = field(R.string.settings_email, InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS)
        password = field(R.string.settings_password, InputType.TYPE_TEXT_VARIATION_PASSWORD)
        action = Button(this).apply { setOnClickListener { onAction() } }

        listOf(status, instance, email, password, action).forEach {
            column.addView(it, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        }
        setContentView(column)
        render()
    }

    override fun onDestroy() {
        worker.shutdown()
        super.onDestroy()
    }

    private fun field(label: Int, variation: Int): EditText = EditText(this).apply {
        setHint(label)
        inputType = InputType.TYPE_CLASS_TEXT or variation
        setSingleLine()
    }

    private fun render() {
        val signedIn = store.isSignedIn()
        status.setText(if (signedIn) R.string.settings_signed_in else R.string.settings_signed_out)
        action.setText(if (signedIn) R.string.settings_sign_out else R.string.settings_sign_in)
        listOf(instance, email, password).forEach { it.isEnabled = !signedIn }
        if (signedIn) instance.setText(store.baseUrl)
    }

    private fun onAction() {
        if (store.isSignedIn()) {
            store.clear()
            password.text.clear()
            render()
            return
        }
        val baseUrl = LumiaParsers.normalizeBaseUrl(instance.text.toString())
        if (baseUrl == null) {
            status.setText(R.string.settings_invalid_instance)
            return
        }
        val emailValue = email.text.toString().trim()
        val passwordValue = password.text.toString()
        action.isEnabled = false
        worker.execute {
            val result = api.signIn(baseUrl, emailValue, passwordValue)
            runOnUiThread {
                action.isEnabled = true
                when (result) {
                    SignInResult.Success -> {
                        password.text.clear()
                        render()
                    }
                    SignInResult.BadCredentials -> status.setText(R.string.settings_bad_credentials)
                    SignInResult.SecondFactorRequired -> status.setText(R.string.settings_second_factor)
                    SignInResult.Failed -> status.setText(R.string.settings_failed)
                }
            }
        }
    }

    private companion object {
        const val PADDING_DP = 24
    }
}
