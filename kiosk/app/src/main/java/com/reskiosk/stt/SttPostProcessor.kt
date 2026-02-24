package com.reskiosk.stt

import com.k2fsa.sherpa.onnx.OfflinePunctuation

object SttPostProcessor {

    /**
     * Applies domain-aware text correction to raw Sherpa STT output.
     *
     * The Zipformer English model (no hotword boosting) frequently
     * mishears ResKiosk-specific vocabulary. This function applies a prioritized
     * correction pipeline before the transcript leaves the device.
     *
     * Pipeline order:
     *   1. Lowercase + trim (normalize input)
     *   2. Phrase corrections (multi-word, applied first to prevent partial word conflicts)
     *   3. Word corrections (single token replacements)
     *   4. toSentenceCase (capitalize first letter of result)
     *
     * Called from KioskViewModel.processAudio() after transcribeBuffer() returns.
     */
    fun process(raw: String): String {
        return process(raw, punctuator = null)
    }

    /**
     * Enhanced pipeline with optional punctuation restoration.
     * Pass the punctuator only for Zipformer (English/JA) output.
     * Whisper already produces punctuated text — do NOT re-punctuate it.
     *
     * Pipeline order: lowercase/trim → collapse duplicates → strip fillers →
     * time normalization → fuzzy domain (edit-distance 1) → phrase corrections →
     * word corrections → punctuation → toSentenceCase.
     */
    fun process(raw: String, punctuator: OfflinePunctuation?): String {
        if (raw.isBlank()) return raw

        var text = raw.lowercase().trim()
        text = collapseDuplicates(text)              // Pass A: Zipformer repetition artifacts
        text = stripFillers(text)                    // Pass B: uh, um, like, etc.
        text = applyTimeNormalization(text)          // Pass C: "seven am" → "7 am"
        text = applyFuzzyDomainCorrection(text)     // Pass D: edit-distance 1 only
        text = applyPhraseCorrections(text)         // multi-word corrections
        text = applyWordCorrections(text)            // single-word corrections
        if (punctuator != null) {
            try {
                text = punctuator.addPunctuation(text)
                text = normalizeCjkPunctuation(text)
            } catch (_: Exception) { /* fallback: continue without punctuation */ }
        }
        text = toSentenceCase(text)
        return text
    }

    /** Collapse repeated words (e.g. "where where is the food" → "where is the food"). */
    private fun collapseDuplicates(text: String): String {
        return text.replace(Regex("\\b(\\w+)( \\1)+\\b"), "$1")
    }

    private val fillerWords = setOf(
        "uh", "um", "uhh", "umm", "erm", "ah", "ahh",
        "like", "you know", "i mean", "so", "well",
        "basically", "literally", "actually"
    )

    private fun stripFillers(text: String): String {
        var result = text
        fillerWords.forEach { filler ->
            result = result.replace(
                Regex("\\b${Regex.escape(filler)}\\b,?\\s*"), " "
            )
        }
        return result.trim().replace(Regex("\\s+"), " ")
    }

    private val timeExpressions = mapOf(
        "seven am" to "7 am",
        "seven a m" to "7 am",
        "twelve noon" to "12 noon",
        "twelve pm" to "12 pm",
        "six pm" to "6 pm",
        "six p m" to "6 pm",
        "nine pm" to "9 pm",
        "nine p m" to "9 pm",
        "nine am" to "9 am",
        "eight am" to "8 am",
        "eight pm" to "8 pm",
        "three pm" to "3 pm",
        "five pm" to "5 pm",
        "five am" to "5 am",
    )

    private fun applyTimeNormalization(text: String): String {
        var result = text
        timeExpressions.forEach { (wrong, right) ->
            result = result.replace(wrong, right)
        }
        return result
    }

    private val highRiskDomainWords = setOf(
        "registration", "medical", "evacuation", "wristband",
        "volunteer", "clinic", "canteen", "gymnasium", "abellana",
        "blanket", "rescue", "paracetamol", "announcement",
        "distribution", "dehydration", "rehydration"
    )

    private fun applyFuzzyDomainCorrection(text: String): String {
        val words = text.split(" ").toMutableList()
        for (i in words.indices) {
            val word = words[i]
            if (word.length < 5) continue
            if (word in highRiskDomainWords) continue
            val closest = highRiskDomainWords.minByOrNull { editDistance(word, it) }
                ?: continue
            if (editDistance(word, closest) == 1) {
                words[i] = closest
            }
        }
        return words.joinToString(" ")
    }

    private fun editDistance(a: String, b: String): Int {
        val dp = Array(a.length + 1) { IntArray(b.length + 1) }
        for (i in 0..a.length) dp[i][0] = i
        for (j in 0..b.length) dp[0][j] = j
        for (i in 1..a.length) {
            for (j in 1..b.length) {
                dp[i][j] = if (a[i - 1] == b[j - 1]) dp[i - 1][j - 1]
                else 1 + minOf(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
            }
        }
        return dp[a.length][b.length]
    }

    private fun normalizeCjkPunctuation(text: String): String {
        return text
            .replace('，', ',')
            .replace('。', '.')
            .replace('？', '?')
            .replace('！', '!')
            .replace('；', ';')
            .replace('：', ':')
            .replace('\u201C', '"')  // "
            .replace('\u201D', '"')  // "
            .replace('\u2018', '\'') // '
            .replace('\u2019', '\'') // '
    }

    private fun toSentenceCase(text: String): String {
        if (text.isEmpty()) return text
        return text[0].uppercaseChar() + text.substring(1)
    }

    // ─────────────────────────────────────────────────────────────────────────
    // PHRASE CORRECTIONS
    // Applied before word corrections to catch multi-word mishearings.
    // Order matters — longer/more specific phrases first.
    // ─────────────────────────────────────────────────────────────────────────
    private val phraseCorrections: Map<String, String> = mapOf(

        // ── ResKiosk system name ──────────────────────────────────────────────
        "res kiosk"             to "reskiosk",
        "risk kiosk"            to "reskiosk",
        "res key ask"           to "reskiosk",
        "risk you ask"          to "reskiosk",
        "res key osk"           to "reskiosk",
        "hello rescuesque"      to "hello ResKiosk",
        "rescuesque"            to "ResKiosk",

        // ── Registration desk / process ───────────────────────────────────────
        "registration desk"     to "registration desk",
        "reg station desk"      to "registration desk",
        "reg is tray shun"      to "registration",
        "red is tray shun"      to "registration",
        "rich is tray shun"     to "registration",
        "registration slip"     to "registration slip",
        "reg slip"              to "registration slip",
        "family number"         to "family number",
        "fam lee number"        to "family number",

        // ── Relief goods ──────────────────────────────────────────────────────
        "relief goods"          to "relief goods",
        "relief good"           to "relief goods",
        "re leaf goods"         to "relief goods",
        "re leaf good"          to "relief goods",
        "release goods"         to "relief goods",
        "real if goods"         to "relief goods",

        // ── Medical station ───────────────────────────────────────────────────
        "medical station"       to "medical station",
        "medic all station"     to "medical station",
        "medical stay shun"     to "medical station",
        "medicine station"      to "medical station",
        "med station"           to "medical station",
        "first aid station"     to "first aid station",
        "first eight station"   to "first aid station",
        "first aid"             to "first aid",
        "first eight"           to "first aid",

        // ── Evacuation center ─────────────────────────────────────────────────
        "evacuation center"     to "evacuation center",
        "evac you asian center" to "evacuation center",
        "evac center"           to "evacuation center",
        "evac you asian"        to "evacuation",
        "evac nation center"    to "evacuation center",
        "evac nation"           to "evacuation",

        // ── Covered court ─────────────────────────────────────────────────────
        "covered court"         to "covered court",
        "cover court"           to "covered court",
        "covered cord"          to "covered court",

        // ── Administration building ───────────────────────────────────────────
        "administration building" to "administration building",
        "admin building"        to "administration building",
        "admin is tray shun"    to "administration",

        // ── Main lobby ────────────────────────────────────────────────────────
        "main lobby"            to "main lobby",
        "main lob be"           to "main lobby",
        "main lob"              to "main lobby",

        // ── Sleeping area ─────────────────────────────────────────────────────
        "sleeping area"         to "sleeping area",
        "sleeping areas"        to "sleeping areas",
        "sleep in area"         to "sleeping area",

        // ── Comfort room ──────────────────────────────────────────────────────
        "comfort room"          to "comfort room",
        "comfort rooms"         to "comfort rooms",
        "comfort rum"           to "comfort room",
        "come for room"         to "comfort room",

        // ── Wristband ─────────────────────────────────────────────────────────
        "wrist band"            to "wristband",
        "wrist van"             to "wristband",
        "wrist ban"             to "wristband",
        "rest band"             to "wristband",

        // ── Charging station ──────────────────────────────────────────────────
        "charging station"      to "charging station",
        "charging stay shun"    to "charging station",
        "charge station"        to "charging station",

        // ── Drinking water ────────────────────────────────────────────────────
        "drinking water"        to "drinking water",
        "drink in water"        to "drinking water",
        "drink water"           to "drinking water",
        "drinking water station" to "drinking water station",

        // ── Water station ─────────────────────────────────────────────────────
        "water station"         to "water station",
        "water stay shun"       to "water station",

        // ── Family tracing ────────────────────────────────────────────────────
        "family tracing"        to "family tracing",
        "family tracing desk"   to "family tracing desk",
        "family trace in"       to "family tracing",

        // ── Loudspeaker ───────────────────────────────────────────────────────
        "loudspeaker"           to "loudspeaker",
        "loud speaker"          to "loudspeaker",
        "loud speak her"        to "loudspeaker",

        // ── Go home / return ──────────────────────────────────────────────────
        "go home"               to "go home",
        "is it safe to go home" to "is it safe to go home",
        "is it safe to return"  to "is it safe to return",
        "return home"           to "return home",

        // ── CDRRMO ────────────────────────────────────────────────────────────
        "city disaster"         to "city disaster",
        "disaster response"     to "disaster response",
        "disaster risk"         to "disaster risk",

        // ── Emergency mode ────────────────────────────────────────────────────
        "emergency mode"        to "emergency mode",
        "emergency mo"          to "emergency mode",

        // ── Oral rehydration ──────────────────────────────────────────────────
        "oral rehydration"      to "oral rehydration",
        "oral re hydration"     to "oral rehydration",
        "oral rehydration solution" to "oral rehydration solution",
        "rehydration solution"  to "rehydration solution",
        "oh are us"             to "ors",

        // ── Lost and found ────────────────────────────────────────────────────
        "lost and found"        to "lost and found",
        "lost n found"          to "lost and found",
        "loss and found"        to "lost and found",

        // ── Volunteer ─────────────────────────────────────────────────────────
        "volunteer ear"         to "volunteer",
        "vole in tier"          to "volunteer",
        "vole un tier"          to "volunteer",

    )

    private fun applyPhraseCorrections(text: String): String {
        var result = text
        // Sort by key length descending so longer phrases match before subsets
        phraseCorrections.entries
            .sortedByDescending { it.key.length }
            .forEach { (wrong, right) ->
                result = result.replace(wrong, right)
            }
        return result
    }

    // ─────────────────────────────────────────────────────────────────────────
    // WORD CORRECTIONS
    // Single-token replacements applied after phrase corrections.
    // These are whole-word replacements — surrounded by word boundaries.
    // ─────────────────────────────────────────────────────────────────────────
    private val wordCorrections: Map<String, String> = mapOf(

        // ── Greetings ──────────────────────────────────────────────────────────
        "hullo"             to "hello",

        // ── Registration ──────────────────────────────────────────────────────
        "agistration"       to "registration",
        "registation"       to "registration",
        "registrasyon"      to "registration",
        "regestration"      to "registration",
        "registrashun"      to "registration",
        "regstration"       to "registration",
        "rejistration"      to "registration",

        // ── Medical ───────────────────────────────────────────────────────────
        "medicial"          to "medical",
        "medikal"           to "medical",
        "medecal"           to "medical",
        "medicle"           to "medical",
        "medikul"           to "medical",
        "medcal"            to "medical",
        "medisin"           to "medicine",
        "medicin"           to "medicine",

        // ── Evacuation ────────────────────────────────────────────────────────
        "evacation"         to "evacuation",
        "evakuasyon"        to "evacuation",
        "evakuation"        to "evacuation",
        "evacution"         to "evacuation",
        "evaccuation"       to "evacuation",
        "evacuasyon"        to "evacuation",

        // ── Volunteer ─────────────────────────────────────────────────────────
        "volunter"          to "volunteer",
        "voluntir"          to "volunteer",
        "bolunteer"         to "volunteer",
        "boluntir"          to "volunteer",
        "volunter"          to "volunteer",
        "voluntear"         to "volunteer",

        // ── Wristband ─────────────────────────────────────────────────────────
        "wristvan"          to "wristband",
        "wristbend"         to "wristband",
        "ristband"          to "wristband",
        "wristbad"          to "wristband",

        // ── Announcement ─────────────────────────────────────────────────────
        "anouncement"       to "announcement",
        "anounsement"       to "announcement",
        "anouncement"       to "announcement",
        "announcment"       to "announcement",
        "announcemnt"       to "announcement",

        // ── Gymnasium ─────────────────────────────────────────────────────────
        "gymnasium"         to "gymnasium",
        "jimnazyum"         to "gymnasium",
        "gimnasium"         to "gymnasium",
        "gymasium"          to "gymnasium",
        "gymanasium"        to "gymnasium",
        "gimnazium"         to "gymnasium",

        // ── Sleeping ──────────────────────────────────────────────────────────
        "sleepin"           to "sleeping",
        "sleping"           to "sleeping",
        "slepping"          to "sleeping",

        // ── Canteen ───────────────────────────────────────────────────────────
        "cantin"            to "canteen",
        "kanteen"           to "canteen",
        "kantine"           to "canteen",
        "cantina"           to "canteen",
        "cantene"           to "canteen",

        // ── Clinic ────────────────────────────────────────────────────────────
        "klinik"            to "clinic",
        "clinik"            to "clinic",
        "clenic"            to "clinic",
        "clinicc"           to "clinic",

        // ── Emergency ────────────────────────────────────────────────────────
        "emergeny"          to "emergency",
        "emergenci"         to "emergency",
        "emerjency"         to "emergency",
        "emerjensi"         to "emergency",
        "emrgency"          to "emergency",

        // ── ResKiosk (STT mishearing) ────────────────────────────────────────
        "rescuesque"        to "ResKiosk",
        "resquesque"        to "ResKiosk",

        // ── Safety ────────────────────────────────────────────────────────────
        "safty"             to "safety",
        "savety"            to "safety",
        "safeti"            to "safety",

        // ── Available ─────────────────────────────────────────────────────────
        "availble"          to "available",
        "availabel"         to "available",
        "availabl"          to "available",
        "avaible"           to "available",

        // ── Distribution ──────────────────────────────────────────────────────
        "distrubution"      to "distribution",
        "distibution"       to "distribution",
        "distribushun"      to "distribution",
        "distributon"       to "distribution",

        // ── Assistance ────────────────────────────────────────────────────────
        "asistance"         to "assistance",
        "assistanse"        to "assistance",
        "asistence"         to "assistance",
        "assistence"        to "assistance",

        // ── Registration-adjacent ─────────────────────────────────────────────
        "resitration"       to "registration",
        "redgistration"     to "registration",

        // ── Hygiene ───────────────────────────────────────────────────────────
        "higiene"           to "hygiene",
        "higyene"           to "hygiene",
        "hygene"            to "hygiene",
        "hygeiene"          to "hygiene",

        // ── Dehydration ───────────────────────────────────────────────────────
        "dehydrasyon"       to "dehydration",
        "deydration"        to "dehydration",
        "dehydrashun"       to "dehydration",

        // ── Rehydration ───────────────────────────────────────────────────────
        "rehydrasyon"       to "rehydration",
        "reydration"        to "rehydration",

        // ── Shelter ───────────────────────────────────────────────────────────
        "shalter"           to "shelter",
        "sheltur"           to "shelter",
        "sheltir"           to "shelter",

        // ── Blanket ───────────────────────────────────────────────────────────
        "blankit"           to "blanket",
        "blankut"           to "blanket",
        "blanket"           to "blanket",

        // ── Rescue ────────────────────────────────────────────────────────────
        "riskyou"           to "rescue",
        "reskyu"            to "rescue",
        "rescew"            to "rescue",
        "rescyou"           to "rescue",

        // ── Seizure ───────────────────────────────────────────────────────────
        "seezure"           to "seizure",
        "seisure"           to "seizure",
        "seezuer"           to "seizure",

        // ── Diarrhea ──────────────────────────────────────────────────────────
        "diarrea"           to "diarrhea",
        "diarreia"          to "diarrhea",
        "dyarya"            to "diarrhea",
        "diarya"            to "diarrhea",
        "dairhea"           to "diarrhea",

        // ── Paracetamol ───────────────────────────────────────────────────────
        "paracetamoul"      to "paracetamol",
        "paresitamol"       to "paracetamol",
        "parasitamol"       to "paracetamol",
        "paracitamol"       to "paracetamol",
        "parasetamol"       to "paracetamol",

        // ── Antibiotics ───────────────────────────────────────────────────────
        "antibiotik"        to "antibiotics",
        "antibyotik"        to "antibiotics",
        "antibyotics"       to "antibiotics",

        // ── Allergy ───────────────────────────────────────────────────────────
        "alerji"            to "allergy",
        "alergy"            to "allergy",
        "allerji"           to "allergy",

        // ── Wheelchair ───────────────────────────────────────────────────────
        "weel chair"        to "wheelchair",
        "weilchair"         to "wheelchair",
        "weelchair"         to "wheelchair",

        // ── Ambulance ─────────────────────────────────────────────────────────
        "ambulanse"         to "ambulance",
        "ambulanse"         to "ambulance",
        "anbulance"         to "ambulance",

        // ── Abellana ──────────────────────────────────────────────────────────
        "abellanna"         to "abellana",
        "abelana"           to "abellana",
        "abelanna"          to "abellana",
        "abillana"          to "abellana",

        // ── Government ───────────────────────────────────────────────────────
        "gobernment"        to "government",
        "goverment"         to "government",
        "governmint"        to "government",

        // ── Coordinate ───────────────────────────────────────────────────────
        "cordinate"         to "coordinate",
        "koordinate"        to "coordinate",
        "cordenate"         to "coordinate",

        // ── Pregnant ──────────────────────────────────────────────────────────
        "pregnent"          to "pregnant",
        "pragnant"          to "pregnant",
        "pregnunt"          to "pregnant",

        // ── Counselor ────────────────────────────────────────────────────────
        "counsilor"         to "counselor",
        "counsler"          to "counselor",
        "counsellor"        to "counselor",

        // ── Psychological ─────────────────────────────────────────────────────
        "sykolohikal"       to "psychological",
        "psycholojical"     to "psychological",
        "sikolohikal"       to "psychological",

        // ── Antibacterial ─────────────────────────────────────────────────────
        "antibacteryal"     to "antibacterial",
        "antibaktiryal"     to "antibacterial",

        // ── Infection ────────────────────────────────────────────────────────
        "infeksyon"         to "infection",
        "infekshun"         to "infection",
        "infecshun"         to "infection",

        // ── Temperature ───────────────────────────────────────────────────────
        "temperachure"      to "temperature",
        "temperture"        to "temperature",
        "temprature"        to "temperature",

        // ── Dizziness ────────────────────────────────────────────────────────
        "dizines"           to "dizziness",
        "dizzines"          to "dizziness",
        "dizyness"          to "dizziness",

        // ── Compression ───────────────────────────────────────────────────────
        "compreson"         to "compression",
        "kompreshun"        to "compression",

        // ── Bandage ───────────────────────────────────────────────────────────
        "bandaj"            to "bandage",
        "bendage"           to "bandage",
        "bandege"           to "bandage",

        // ── Fracture ──────────────────────────────────────────────────────────
        "frakture"          to "fracture",
        "frakcure"          to "fracture",
        "fractur"           to "fracture",

        // ── Accessible ───────────────────────────────────────────────────────
        "acsessible"        to "accessible",
        "accesible"         to "accessible",
        "accessable"        to "accessible",

    )

    private fun applyWordCorrections(text: String): String {
        var result = text
        wordCorrections.forEach { (wrong, right) ->
            // Whole-word replacement using regex word boundaries
            result = result.replace(
                Regex("\\b${Regex.escape(wrong)}\\b"),
                right
            )
        }
        return result
    }
}
