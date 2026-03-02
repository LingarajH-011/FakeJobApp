[app]
title = FakeJobDetector
package.name = fakejobdetector
package.domain = org.fakejob
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,pkl,csv,txt,json
version = 1.0
requirements = python3,kivy==2.3.0,kivymd==1.2.0,requests,numpy,joblib,pillow

orientation = portrait
fullscreen = 0
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.sdk = 33
android.accept_sdk_license = True
android.arch = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
