package app.lumia.auto

object ControllerPolicy {
    private val knownPackages = setOf(
        "android",
        "com.android.systemui",
        "com.android.car.media",
        "com.android.car.mediacenter",
        "com.google.android.projection.gearhead",
        "com.google.android.autosimulator",
        "com.google.android.carassistant",
        "com.google.android.googlequicksearchbox",
        "com.google.android.apps.automotive.templates.host",
        "com.google.android.apps.automotive.media",
    )

    fun isAllowed(callerPackage: String, ownPackage: String, trustedBySystem: Boolean): Boolean =
        callerPackage == ownPackage || callerPackage in knownPackages || trustedBySystem
}
