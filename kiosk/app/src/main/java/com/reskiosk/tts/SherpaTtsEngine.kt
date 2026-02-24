package com.reskiosk.tts

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.util.Log
import com.k2fsa.sherpa.onnx.OfflineTts
import com.k2fsa.sherpa.onnx.OfflineTtsConfig
import com.k2fsa.sherpa.onnx.OfflineTtsModelConfig
import com.k2fsa.sherpa.onnx.OfflineTtsVitsModelConfig
import com.reskiosk.ModelConstants
import java.io.File

class SherpaTtsEngine private constructor(
    context: Context,
    modelsDir: File,
    modelName: String,
    private val speed: Float = 0.95f
) {
    companion object {
        fun forLanguage(context: Context, langCode: String): SherpaTtsEngine {
            val modelsBase = File(context.filesDir, ModelConstants.MODELS_BASE_DIR)
            return when (langCode) {
                "en" -> SherpaTtsEngine(context,
                    File(modelsBase, ModelConstants.TTS_DIR_EN),
                    onnxNameFromDir(ModelConstants.TTS_DIR_EN),
                    speed = 0.95f)
                "es" -> SherpaTtsEngine(context,
                    File(modelsBase, ModelConstants.TTS_DIR_ES),
                    onnxNameFromDir(ModelConstants.TTS_DIR_ES),
                    speed = 0.92f)   // Spanish benefits from slightly slower pace
                "tl" -> {
                    Log.w("SherpaTTS", "No Filipino TTS model available; falling back to English")
                    SherpaTtsEngine(context,
                        File(modelsBase, ModelConstants.TTS_DIR_EN),
                        onnxNameFromDir(ModelConstants.TTS_DIR_EN),
                        speed = 0.95f)
                }
                "ja" -> {
                    Log.w("SherpaTTS", "No Japanese TTS model available; falling back to English")
                    SherpaTtsEngine(context,
                        File(modelsBase, ModelConstants.TTS_DIR_EN),
                        onnxNameFromDir(ModelConstants.TTS_DIR_EN),
                        speed = 0.90f)
                }
                "ko" -> SherpaTtsEngine(context,
                    File(modelsBase, ModelConstants.TTS_DIR_KO),
                    onnxNameFromDir(ModelConstants.TTS_DIR_KO),
                    speed = 0.95f)
                else -> SherpaTtsEngine(context,
                    File(modelsBase, ModelConstants.TTS_DIR_EN),
                    onnxNameFromDir(ModelConstants.TTS_DIR_EN),
                    speed = 0.95f)
            }
        }

        private fun onnxNameFromDir(dirName: String): String {
            val prefix = dirName.removePrefix("vits-piper-")
            return "$prefix.onnx"
        }
    }

    private var tts: OfflineTts? = null
    private val sampleRate = 22050 // VITS usually 22050
    private var audioTrack: AudioTrack? = null
    @Volatile private var isStopped = false

    init {
        try {
            if (!modelsDir.exists()) {
                Log.e("SherpaTTS", "Models not found in filesDir. Setup Required: ${modelsDir.absolutePath}")
            } else {
                Log.i("SherpaTTS", "Loading from FilesDir: $modelsDir")
                val modelPath = File(modelsDir, modelName).absolutePath
                val tokensPath = File(modelsDir, "tokens.txt").absolutePath
                val dataPath = File(modelsDir, "espeak-ng-data").absolutePath

                val config = OfflineTtsConfig(
                    model = OfflineTtsModelConfig(
                        vits = OfflineTtsVitsModelConfig(
                            model = modelPath,
                            tokens = tokensPath,
                            dataDir = dataPath,
                        ),
                        numThreads = 2,       // ↑ from 1 — better synthesis throughput
                        debug = false,        // disable debug logging in production
                        provider = "cpu",
                    ),
                    maxNumSentences = 1       // CRITICAL for streaming — forces per-sentence callback
                )
                tts = OfflineTts(assetManager = null, config = config)

                // 2-second AudioTrack buffer for smooth streaming playback
                audioTrack = AudioTrack.Builder()
                    .setAudioAttributes(
                        AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_MEDIA)
                            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                            .build()
                    )
                    .setAudioFormat(
                        AudioFormat.Builder()
                            .setEncoding(AudioFormat.ENCODING_PCM_FLOAT)
                            .setSampleRate(sampleRate)
                            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                            .build()
                    )
                    .setBufferSizeInBytes(sampleRate * 4 * 2)  // 2 seconds buffer
                    .setTransferMode(AudioTrack.MODE_STREAM)
                    .build()
            }

        } catch (e: Exception) {
            Log.e("SherpaTTS", "Failed to init TTS", e)
        }
    }

    /**
     * Streams TTS output — begins playing the first sentence while
     * synthesizing remaining sentences. Uses generateWithCallback() with
     * maxNumSentences=1 so each sentence fires its own callback.
     *
     * Pass the FULL multi-sentence response as one string. Do NOT split manually.
     */
    fun speak(text: String) {
        if (text.isEmpty()) return
        isStopped = false
        Log.i("SherpaTTS", "Speaking (speed=${speed}): $text")

        Thread {
            try {
                var isStarted = false
                tts?.generateWithCallback(text, sid = 0, speed = speed) { samples ->
                    if (isStopped) {
                        return@generateWithCallback 0 // stop generating
                    }

                    if (!isStarted) {
                        try {
                            audioTrack?.play()
                            isStarted = true
                        } catch (e: Exception) {
                            Log.e("SherpaTTS", "Error starting AudioTrack", e)
                        }
                    }

                    if (samples.isNotEmpty()) {
                        audioTrack?.write(samples, 0, samples.size, AudioTrack.WRITE_BLOCKING)
                    }

                    1 // continue generating
                }
            } catch (e: Exception) {
                Log.e("SherpaTTS", "Error generating audio", e)
            }
        }.start()
    }

    /** True while AudioTrack is actively playing TTS audio */
    fun isPlaying(): Boolean {
        return !isStopped && audioTrack?.playState == AudioTrack.PLAYSTATE_PLAYING
    }

    fun stop() {
        isStopped = true
        try {
            audioTrack?.pause()
            audioTrack?.flush()
        } catch (e: Exception) {
            Log.e("SherpaTTS", "Error stopping playback", e)
        }
    }

    fun release() {
        stop()
        tts?.release()
        audioTrack?.release()
        tts = null
        audioTrack = null
    }
}
