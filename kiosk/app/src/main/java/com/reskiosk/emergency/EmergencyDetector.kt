package com.reskiosk.emergency

/**
 * Tier 1: full-phrase match — high confidence, trigger immediately.
 * Tier 2: single keyword — show confirmation before alerting.
 * Detection runs on both raw and processed transcript.
 */
object EmergencyDetector {

    data class Result(
        val isEmergency: Boolean,
        val tier: Int = 0,  // 1 = full phrase, 2 = keyword
        val triggerPhrase: String? = null
    )

    private val tier1Phrases = setOf(
        "i need immediate help", "i need help now", "help me now",
        "i cannot breathe", "i am having a heart attack",
        "someone is unconscious", "someone collapsed",
        "i am bleeding badly", "severe bleeding",
        "i need an ambulance", "call for help",
        "there is a fire",
        "necesito ayuda ahora", "no puedo respirar",
        "hay un incendio", "alguien está inconsciente",
        "tasukete kudasai", "kyuukyuu desu", "hi ga deta"
    )

    private val tier2Keywords = setOf(
        "fire", "fuego", "kaji",
        "dying", "muero",
        "unconscious", "inconsciente",
        "emergency", "emergencia", "kyuukyuu",
        "ambulance", "ambulancia"
    )

    fun detect(processedTranscript: String, rawTranscript: String): Result {
        val p = processedTranscript.lowercase().trim()
        val r = rawTranscript.lowercase().trim()

        for (phrase in tier1Phrases) {
            if (p.contains(phrase) || r.contains(phrase)) {
                return Result(isEmergency = true, tier = 1, triggerPhrase = phrase)
            }
        }
        for (keyword in tier2Keywords) {
            val pattern = Regex("\\b${Regex.escape(keyword)}\\b")
            if (pattern.containsMatchIn(p) || pattern.containsMatchIn(r)) {
                return Result(isEmergency = true, tier = 2, triggerPhrase = keyword)
            }
        }
        return Result(isEmergency = false)
    }
}
