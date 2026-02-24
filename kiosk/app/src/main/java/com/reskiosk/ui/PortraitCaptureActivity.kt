package com.reskiosk.ui

import com.journeyapps.barcodescanner.CaptureActivity

/**
 * Forces the barcode scanner to open in portrait/vertical orientation
 * instead of the default landscape mode.
 *
 * Registered in AndroidManifest.xml with screenOrientation="portrait".
 */
class PortraitCaptureActivity : CaptureActivity()
