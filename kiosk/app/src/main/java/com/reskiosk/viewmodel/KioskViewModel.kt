package com.reskiosk.viewmodel

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.reskiosk.audio.AudioRecorder
import com.reskiosk.emergency.EmergencyDetector
import com.reskiosk.emergency.EmergencyStrings
import com.reskiosk.network.HubApiClient
import com.reskiosk.stt.SherpaSttEngine
import com.reskiosk.stt.analyzeIntonation
import com.reskiosk.tts.SherpaTtsEngine
import com.k2fsa.sherpa.onnx.OfflinePunctuation
import com.k2fsa.sherpa.onnx.OfflinePunctuationConfig
import com.k2fsa.sherpa.onnx.OfflinePunctuationModelConfig
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.Collections
import java.util.UUID

// States
sealed class KioskState {
    object Idle : KioskState()
    object Listening : KioskState()
    object Transcribing : KioskState()
    object Processing : KioskState()
    data class Speaking(val text: String) : KioskState()
    data class Clarification(val question: String, val options: List<String>) : KioskState()
    data class Error(val message: String) : KioskState()
    object TerminatingSession : KioskState()
    data class EmergencyConfirmation(val transcript: String) : KioskState()
    object EmergencyActive : KioskState()
}

// Data class for Chat Frame
data class ChatMessage(val isUser: Boolean, val text: String, val id: String = "")

// Extension to convert ALL-CAPS STT output to proper sentence case
private fun String.toSentenceCase(): String {
    if (isBlank()) return this
    return lowercase().replaceFirstChar { it.uppercase() }
}


class KioskViewModel(application: Application) : AndroidViewModel(application) {

    private val _uiState = MutableStateFlow<KioskState>(KioskState.Idle)
    val uiState = _uiState.asStateFlow()

    // Preferences
    private val prefs = application.getSharedPreferences("reskiosk_prefs", android.content.Context.MODE_PRIVATE)

    // Heartbeat & Connection
    private var heartbeatJob: Job? = null
    private var failedPings = 0
    
    // Session State
    private var _sessionId = MutableStateFlow<String?>(null)
    val sessionId = _sessionId.asStateFlow()
    
    private val _chatHistory = MutableStateFlow<List<ChatMessage>>(emptyList())
    val chatHistory = _chatHistory.asStateFlow()

    // Inactivity auto-timeout
    private var inactivityJob: Job? = null
    private val INACTIVITY_TIMEOUT_MS = 60_000L  // 1 minute

    private var _punctuator: OfflinePunctuation? = null

    init {
        // Persistent kiosk_id: same key as HubClient so heartbeat and query use same ID
        val kioskId = prefs.getString("kiosk_id", null)
            ?: UUID.randomUUID().toString().also { prefs.edit().putString("kiosk_id", it).apply() }
        HubApiClient.setKioskId(kioskId)

        // Start heartbeat if URL exists
        if (getHubUrl().isNotBlank()) {
            startHeartbeat()
        }
        
        // Initialize punctuation model
        try {
            val punctDir = File(application.filesDir, "sherpa-models/" + com.reskiosk.ModelConstants.PUNCTUATION_DIR)
            if (punctDir.exists()) {
                val modelPath = File(punctDir, "model.onnx").absolutePath
                val config = OfflinePunctuationConfig(
                    model = OfflinePunctuationModelConfig(
                        ctTransformer = modelPath,
                        numThreads = 1,
                        debug = false,
                        provider = "cpu"
                    )
                )
                _punctuator = OfflinePunctuation(assetManager = null, config = config)
                Log.i("KioskVM", "Punctuation model loaded successfully.")
            } else {
                Log.w("KioskVM", "Punctuation model directory not found.")
            }
        } catch (e: Exception) {
            Log.e("KioskVM", "Failed to load punctuation model", e)
        }
    }

    private fun startHeartbeat() {
        heartbeatJob?.cancel()
        heartbeatJob = viewModelScope.launch {
            while (isActive) {
                val url = getHubUrl()
                if (url.isNotBlank()) {
                    try {
                        val api = HubApiClient.getService(url)
                        api.ping()
                        failedPings = 0
                    } catch (e: Exception) {
                        failedPings++
                        android.util.Log.e("KioskViewModel", "Heartbeat failed ($failedPings)", e)
                        if (failedPings == 3) {
                            // We only log this once when we first hit the threshold.
                            // Do NOT disconnectHub() here so we auto-reconnect once the hub recovers.
                            android.util.Log.e("KioskViewModel", "Connection lost, but keeping hub URL to auto-reconnect.")
                        }
                    }
                }
                delay(20_000L) // Poll every 20 seconds per spec
            }
        }
    }
    private val _transcript = MutableStateFlow("")
    val transcript = _transcript.asStateFlow()

    // Selected language — restored from SharedPreferences
    private val _selectedLanguage = MutableStateFlow(
        prefs.getString("selected_language", "en") ?: "en"
    )
    val selectedLanguage = _selectedLanguage.asStateFlow()

    fun setLanguage(langCode: String) {
        _selectedLanguage.value = langCode
        Log.i("KioskVM", "Language set to: $langCode")

        // Persist selection
        prefs.edit().putString("selected_language", langCode).apply()

        // Rebuild STT/TTS engine for selected language on a background thread
        // to prevent UI freezing while loading heavy ONNX models
        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            val oldStt = stt
            stt = null // Disable listening temporarily
            oldStt?.release()
            stt = SherpaSttEngine.forLanguage(getApplication(), langCode)
            
            val oldTts = tts
            tts = null
            oldTts?.release()
            tts = SherpaTtsEngine.forLanguage(getApplication(), langCode)
        }
    }

    // Dependencies — STT uses factory for language-aware model selection
    private val recorder = AudioRecorder()
    private var stt: SherpaSttEngine? = SherpaSttEngine.forLanguage(application, _selectedLanguage.value)
    private var tts: SherpaTtsEngine? = SherpaTtsEngine.forLanguage(application, _selectedLanguage.value)

    // State
    private var recordedSamples: MutableList<Float> = Collections.synchronizedList(mutableListOf())
    private var lastQueryEnglish: String? = null
    private var lastQueryOriginal: String? = null

    // Preferences

    fun getHubUrl(): String = prefs.getString("hub_url", "") ?: ""

    fun saveHubUrl(url: String) {
        prefs.edit().putString("hub_url", url.trim()).apply()
        android.util.Log.i("KioskViewModel", "Hub URL saved: ${url.trim()}, starting heartbeat")
        startHeartbeat()
    }

    fun disconnectHub() {
        prefs.edit().remove("hub_url").apply()
        heartbeatJob?.cancel()
        heartbeatJob = null
        failedPings = 0
        endSession()
        android.util.Log.i("KioskViewModel", "Hub disconnected, heartbeat stopped")
    }

    // --- Inactivity Timer ---
    private fun resetInactivityTimer() {
        if (_sessionId.value == null) return // No session, no timer
        inactivityJob?.cancel()
        inactivityJob = viewModelScope.launch {
            delay(INACTIVITY_TIMEOUT_MS)
            Log.i("KioskVM", "Session inactive for ${INACTIVITY_TIMEOUT_MS / 1000}s, terminating")
            _uiState.value = KioskState.TerminatingSession
            tts?.stop()
            recorder.stopRecording()
            delay(2_000L) // Show overlay briefly
            endSession()
        }
    }

    private fun cancelInactivityTimer() {
        inactivityJob?.cancel()
        inactivityJob = null
    }

    // --- Session API ---
    fun startSession() {
        _sessionId.value = UUID.randomUUID().toString()
        _chatHistory.value = emptyList()
        _uiState.value = KioskState.Idle
        // Start continuous background listening for instant zero-latency STT
        recorder.startContinuousListening(viewModelScope)
        resetInactivityTimer()
    }

    fun endSession() {
        val currentSession = _sessionId.value
        cancelInactivityTimer()
        _sessionId.value = null
        _chatHistory.value = emptyList()
        _uiState.value = KioskState.Idle
        _transcript.value = ""
        
        // Notify Hub to clear memory
        if (currentSession != null) {
            val url = getHubUrl()
            if (url.isNotBlank()) {
                viewModelScope.launch {
                    try {
                        val api = HubApiClient.getService(url)
                        api.endSession(currentSession)
                    } catch (e: Exception) {
                        // Ignore backend connection errors on disconnect
                    }
                }
            }
        }
    }

    // --- Inputs ---

    fun startListening() {
        if (stt == null) {
            handleError("Changing language... please wait.")
            return
        }
        // Allow recording from Idle, Speaking, Error, and Clarification; block Emergency and busy states
        val currentState = _uiState.value
        if (currentState !is KioskState.Idle && currentState !is KioskState.Speaking && currentState !is KioskState.Error && currentState !is KioskState.Clarification ||
            currentState is KioskState.EmergencyActive || currentState is KioskState.EmergencyConfirmation) {
            // Stuck-state recovery: if stuck in Processing/Transcribing for too long, force reset
            Log.w("KioskVM", "startListening blocked by state: $currentState — ignoring")
            return
        }
        
        // Stop any previous TTS and clear pre-buffer so we don't record speaker output
        try { recorder.stopRecording() } catch (e: Exception) {}
        tts?.stop()
        recorder.clearPreBuffer()

        viewModelScope.launch {
            delay(150) // Let residual speaker output dissipate before capturing
            if (!isActive) return@launch
            _uiState.value = KioskState.Listening
            _transcript.value = ""
            recordedSamples = Collections.synchronizedList(mutableListOf())
            resetInactivityTimer()
            stt?.beginStream()
            recorder.startRecording { chunk ->
                synchronized(recordedSamples) {
                    // 5-minute cap — eliminates any risk of truncation for long utterances
                    if (recordedSamples.size < 16000 * 300) {
                        recordedSamples.addAll(chunk.toList())
                    }
                }
                // Live streaming STT — partial results update the transcript in real time
                val partialRaw = stt?.feedAndDecodeStream(chunk)
                if (!partialRaw.isNullOrBlank()) {
                    _transcript.value = partialRaw.toSentenceCase()
                }
            }
        }
    }

    fun stopListening() {
        if (_uiState.value != KioskState.Listening) return

        recorder.stopRecording()
        _uiState.value = KioskState.Transcribing

        resetInactivityTimer()

        // Continuous listener stays running in background 
        // to fill the ring buffer for the next tap

        processAudio()
    }

    fun selectClarification(category: String) {
        val qEn = lastQueryEnglish ?: return
        val qOrg = lastQueryOriginal ?: qEn
        resetInactivityTimer()
        performQuery(qEn, qOrg, isRetry = true, category = category)
    }

    fun reset() {
        recorder.stopRecording()
        tts?.stop()
        try { stt?.finishStream() } catch (e: Exception) {}
        _transcript.value = ""
        _uiState.value = KioskState.Idle
    }

    // --- Emergency (see Section 1.1 for inactivity/timer behavior) ---

    fun activateEmergency(transcript: String = "[SOS button]") {
        viewModelScope.launch(Dispatchers.Main) {
            cancelInactivityTimer()
            _uiState.value = KioskState.EmergencyActive
            tts?.speak(EmergencyStrings.get("activated", _selectedLanguage.value))
        }
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val hubUrl = prefs.getString("hub_url", "") ?: ""
                if (hubUrl.isNotBlank()) {
                    val kioskId = prefs.getString("kiosk_id", null) ?: java.util.UUID.randomUUID().toString().also {
                        prefs.edit().putString("kiosk_id", it).apply()
                    }
                    val kioskLocation = prefs.getString("kiosk_location", "Unknown") ?: "Unknown"
                    val api = HubApiClient.getService(hubUrl)
                    api.emergency(
                        mapOf(
                            "kiosk_id" to kioskId,
                            "kiosk_location" to kioskLocation,
                            "transcript" to transcript,
                            "language" to _selectedLanguage.value,
                            "timestamp" to System.currentTimeMillis()
                        )
                    )
                }
            } catch (e: Exception) {
                Log.e("Emergency", "Hub notify failed: ${e.message}")
            }
        }
    }

    fun confirmEmergency(transcript: String) {
        activateEmergency(transcript)
    }

    fun cancelEmergency() {
        _uiState.value = KioskState.Idle
        resetInactivityTimer()
    }

    fun dismissEmergency() {
        _uiState.value = KioskState.Idle
        resetInactivityTimer()
    }

    fun onSosButtonPressed() {
        viewModelScope.launch(Dispatchers.Main) {
            tts?.stop()
            recorder.stopRecording()
            activateEmergency("[SOS button pressed]")
        }
    }

    // --- Logic ---

    private fun processAudio() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val samples: FloatArray
                synchronized(recordedSamples) {
                    samples = recordedSamples.toFloatArray()
                }
                Log.i("KioskVM", "Recorded ${samples.size} samples (${samples.size / 16000f}s)")

                // 0.3s minimum — short enough for "food?", "water?", "help!"
                // but long enough to reject accidental button taps
                if (samples.size < (16000 * 0.3f).toInt()) {
                    withContext(Dispatchers.Main) {
                        handleError("Recording was too short. Please hold the button longer.")
                    }
                    stt?.finishStream()
                    return@launch
                }

                val transcriptRaw = stt?.finishStream() ?: ""
                Log.i("KioskVM", "STT raw transcript: '$transcriptRaw'")

                if (transcriptRaw.isBlank()) {
                    withContext(Dispatchers.Main) { handleError("I didn't hear anything. Please try again.") }
                    return@launch
                }

                // Post-process: corrections + optional punctuation
                // Punctuation only for Zipformer path (en, ja) — Whisper already produces punctuated text
                val lang = _selectedLanguage.value
                val useZipformerPunct = (lang == "en" || lang == "ja")
                val transcriptProcessed = com.reskiosk.stt.SttPostProcessor.process(
                    transcriptRaw,
                    punctuator = if (useZipformerPunct) _punctuator else null
                )
                Log.d("STT", "Raw:       $transcriptRaw")
                Log.d("STT", "Corrected: $transcriptProcessed")

                if (transcriptProcessed.isBlank()) {
                    withContext(Dispatchers.Main) { handleError("I didn't catch that. Please try again.") }
                    return@launch
                }

                // Emergency detection (both raw and processed) — before intonation and performQuery
                val emergencyResult = EmergencyDetector.detect(transcriptProcessed, transcriptRaw)
                if (emergencyResult.isEmergency) {
                    withContext(Dispatchers.Main) {
                        tts?.stop()
                        if (emergencyResult.tier == 1) {
                            activateEmergency(transcriptProcessed)
                        } else {
                            cancelInactivityTimer()
                            _uiState.value = KioskState.EmergencyConfirmation(transcriptProcessed)
                            tts?.speak(EmergencyStrings.get("confirm_prompt", _selectedLanguage.value))
                        }
                    }
                    return@launch
                }

                // Intonation analysis — combine punctuation, acoustic, and lexical signals
                val intonation = analyzeIntonation(
                    rawText = transcriptRaw,
                    punctuatedText = transcriptProcessed,
                    audioSamples = samples
                )
                Log.i("KioskVM", "Intonation: isQuestion=${intonation.isQuestion}, confidence=${intonation.confidence}")

                // Show final transcript and UI on main thread
                withContext(Dispatchers.Main) {
                    _transcript.value = transcriptProcessed
                    _uiState.value = KioskState.Processing
                    val placeholderId = "hub_" + System.currentTimeMillis()
                    val newList = _chatHistory.value.toMutableList()
                    newList.add(ChatMessage(isUser = true, text = transcriptProcessed))
                    newList.add(ChatMessage(isUser = false, text = "Asking hub...", id = placeholderId))
                    _chatHistory.value = newList
                    lastQueryEnglish = transcriptProcessed
                    lastQueryOriginal = transcriptProcessed
                    performQuery(
                    transcriptProcessed, transcriptProcessed,
                    isRetry = false, category = null,
                    placeholderId = placeholderId,
                        queryType = if (intonation.isQuestion) "question" else "statement",
                        intonationConfidence = intonation.confidence
                    )
                }

            } catch (e: Exception) {
                Log.e("KioskVM", "System Error", e)
                withContext(Dispatchers.Main) { handleError("System Error: ${e.message}") }
            }
        }
    }

    private fun performQuery(
        queryEnglish: String, queryOriginal: String, isRetry: Boolean,
        category: String? = null, placeholderId: String? = null,
        queryType: String = "statement", intonationConfidence: Float = 0f
    ) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val hubUrl = prefs.getString("hub_url", "") ?: ""
                if (hubUrl.isBlank()) {
                    withContext(Dispatchers.Main) { handleError("Hub not configured. Please connect to a Hub first.") }
                    return@launch
                }

                val kioskId = prefs.getString("kiosk_id", null)
                    ?: UUID.randomUUID().toString().also { prefs.edit().putString("kiosk_id", it).apply() }
                val payload = mutableMapOf<String, Any>(
                    "center_id" to "center_1",
                    "kiosk_id" to kioskId,
                    "transcript_original" to queryOriginal,
                    "transcript_english" to queryEnglish,
                    "language" to _selectedLanguage.value,
                    "kb_version" to 1,
                    "is_retry" to isRetry,
                    "query_type" to queryType,
                    "intonation_confidence" to intonationConfidence
                )
                if (category != null) payload["selected_category"] = category
                if (_sessionId.value != null) payload["session_id"] = _sessionId.value!!

                Log.i("KioskVM", "Sending query to hub: ${queryEnglish.take(80)}")
                val queryStart = System.currentTimeMillis()
                val api = HubApiClient.getService(hubUrl)
                val response = api.query(payload)
                val queryMs = System.currentTimeMillis() - queryStart
                Log.i("KioskVM", "Hub responded in ${queryMs}ms: type=${response.answerType}")

                withContext(Dispatchers.Main) {
                    if (response.answerType == "NEEDS_CLARIFICATION") {
                        if (placeholderId != null) {
                            _chatHistory.value = _chatHistory.value.filter { it.id != placeholderId }
                        }
                        val clarificationQuestion = "Which category are you asking?"
                        _uiState.value = KioskState.Clarification(
                            clarificationQuestion,
                            response.clarificationCategories ?: emptyList()
                        )
                        tts?.speak(clarificationQuestion)
                        resetInactivityTimer()
                    } else {
                        val finalAnswer = response.answerTextLocalized
                            ?: response.answerTextEn
                            ?: "I'm sorry, I couldn't find an answer."
                        if (placeholderId != null) {
                            _chatHistory.value = _chatHistory.value.map {
                                if (it.id == placeholderId) ChatMessage(isUser = false, text = finalAnswer) else it
                            }
                        } else {
                            val newList = _chatHistory.value.toMutableList()
                            newList.add(ChatMessage(isUser = true, text = queryOriginal))
                            newList.add(ChatMessage(isUser = false, text = finalAnswer))
                            _chatHistory.value = newList
                        }
                        speakAndShow(finalAnswer)
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("KioskViewModel", "Query failed", e)
                withContext(Dispatchers.Main) {
                    if (placeholderId != null) {
                        _chatHistory.value = _chatHistory.value.filter { it.id != placeholderId }
                    }
                    val friendlyMsg = when {
                        e is java.net.ConnectException -> "Cannot reach the Hub. Please check your WiFi connection."
                        e is java.net.SocketTimeoutException -> "The Hub is taking too long to respond. Please try again."
                        e.message?.contains("failed to connect", ignoreCase = true) == true -> "Cannot reach the Hub. Please check your WiFi connection."
                        e.message?.contains("timeout", ignoreCase = true) == true -> "Connection timed out. Please try again."
                        else -> "Something went wrong. Please try again."
                    }
                    handleError(friendlyMsg)
                }
            }
        }
    }

    private fun handleError(msg: String) {
        _uiState.value = KioskState.Error(msg)
        tts?.speak(msg)
        // Auto-reset to Idle after 3s so user can record again
        viewModelScope.launch {
            delay(3000L)
            if (_uiState.value is KioskState.Error) {
                _uiState.value = KioskState.Idle
            }
        }
    }

    private fun speakAndShow(text: String) {
        _uiState.value = KioskState.Speaking(text)
        tts?.speak(text)
        // Wait for TTS to actually finish playing, with a safety timeout
        viewModelScope.launch {
            delay(500L) // Brief initial delay for AudioTrack to start
            val startTime = System.currentTimeMillis()
            while (tts?.isPlaying() == true && System.currentTimeMillis() - startTime < 30_000L) {
                delay(300L)
            }
            delay(500L) // Brief pause after speech ends
            if (_uiState.value is KioskState.Speaking) {
                _uiState.value = KioskState.Idle
            }
            resetInactivityTimer()
        }
    }

    override fun onCleared() {
        super.onCleared()
        cancelInactivityTimer()
        stt?.release()
        tts?.release()
        _punctuator?.release()
        recorder.release()
    }
}
