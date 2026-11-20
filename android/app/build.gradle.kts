plugins {
    id("com.android.application")
}

android {
    namespace = "com.fixit.app"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.fixit.app"
        minSdk = 24          // Android 7.0+ (text-selection actions need 6.0+)
        targetSdk = 37
        versionCode = 4
        versionName = "1.3"
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
            // Signed with the local debug key so it can be sideloaded. Use a real key for Google Play.
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

// No dependencies on purpose: only Android's built-in APIs, for the smallest, lightest app.
