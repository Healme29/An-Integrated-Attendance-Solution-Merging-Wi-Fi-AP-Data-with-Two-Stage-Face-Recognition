# ---------------------------------------------------------------------------
# MLKit (used by mobile_scanner for QR / barcode detection).
#
# MLKit discovers and instantiates its internal registrars by class name via
# reflection (com.google.mlkit.common.internal.ComponentDiscovery). R8 code
# shrinking removes constructors/members that are only reached that way, so in
# a minified release build the registrars cannot be created:
#
#   NoSuchMethodException: com.google.mlkit.common.internal.CommonComponentRegistrar.<init> []
#   NoSuchMethodException: com.google.mlkit.vision.barcode.internal.BarcodeRegistrar.<init> []
#
# The barcode scanner then fails to initialise and mobile_scanner throws
# MobileScannerErrorCode.genericError (NullPointerException on the method
# channel). Keeping the whole MLKit surface fixes the QR scanner without
# disabling R8 for the rest of the app.
# ---------------------------------------------------------------------------
-keep class com.google.mlkit.** { *; }
-keep class com.google.android.gms.internal.mlkit_vision_barcode.** { *; }
-keep class com.google.android.gms.internal.mlkit_common.** { *; }
-keep class com.google.android.gms.internal.mlkit_vision_common.** { *; }
-dontwarn com.google.mlkit.**
