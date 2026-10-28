plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val media3Version = "1.4.1"

android {
    namespace = "app.lumia.auto"
    compileSdk = 34

    defaultConfig {
        applicationId = "app.lumia.auto"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    sourceSets {
        getByName("main").java.srcDir("src/main/kotlin")
        getByName("test").java.srcDir("src/test/kotlin")
    }
}

dependencies {
    implementation("androidx.media3:media3-exoplayer:$media3Version")
    implementation("androidx.media3:media3-session:$media3Version")
    implementation("androidx.media3:media3-datasource:$media3Version")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
}
