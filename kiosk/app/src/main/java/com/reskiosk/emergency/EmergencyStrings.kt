package com.reskiosk.emergency

/** Pre-translated emergency strings. No NLLB at alert time. Fallback to English if key missing. */
object EmergencyStrings {
    fun get(key: String, lang: String): String =
        strings[lang]?.get(key) ?: strings["en"]!![key] ?: key

    private val strings = mapOf(
        "en" to mapOf(
            "confirm_prompt" to "I heard something urgent. Do you need emergency help right now?",
            "confirm_title" to "Do you need emergency help?",
            "confirm_yes" to "YES — CALL FOR HELP",
            "confirm_no" to "No — cancel",
            "activated" to "Help is on the way. A response team has been notified of your location. Stay where you are. You are not alone.",
            "active_title" to "HELP IS ON THE WAY",
            "active_body" to "A response team has been notified of your location. Stay where you are. You are not alone.",
            "dismiss" to "Dismiss"
        ),
        "tl" to mapOf(
            "confirm_prompt" to "Narinig ko ang isang bagay na apurahan. Kailangan mo ba ng tulong ngayon?",
            "confirm_title" to "Kailangan mo ba ng tulong sa emergency?",
            "confirm_yes" to "OO — HUMINGI NG TULONG",
            "confirm_no" to "Hindi — kanselahin",
            "activated" to "Paparating na ang tulong. Naabisuhan na ang response team sa iyong lokasyon. Manatili ka dito. Hindi ka nag-iisa.",
            "active_title" to "PAPARATING NA ANG TULONG",
            "active_body" to "Naabisuhan na ang response team sa iyong lokasyon. Manatili ka dito. Hindi ka nag-iisa.",
            "dismiss" to "Isara"
        ),
        "es" to mapOf(
            "confirm_prompt" to "Escuché algo urgente. ¿Necesitas ayuda de emergencia ahora mismo?",
            "confirm_title" to "¿Necesitas ayuda de emergencia?",
            "confirm_yes" to "SÍ — PEDIR AYUDA",
            "confirm_no" to "No — cancelar",
            "activated" to "La ayuda está en camino. El equipo de respuesta ha sido notificado de tu ubicación. Quédate donde estás. No estás solo.",
            "active_title" to "LA AYUDA ESTÁ EN CAMINO",
            "active_body" to "El equipo de respuesta ha sido notificado. Quédate donde estás. No estás solo.",
            "dismiss" to "Cerrar"
        ),
        "ja" to mapOf(
            "confirm_prompt" to "緊急の言葉が聞こえました。今すぐ助けが必要ですか？",
            "confirm_title" to "緊急の助けが必要ですか？",
            "confirm_yes" to "はい — 助けを呼ぶ",
            "confirm_no" to "いいえ — キャンセル",
            "activated" to "助けが向かっています。対応チームにあなたの場所が通知されました。その場にいてください。一人ではありません。",
            "active_title" to "助けが向かっています",
            "active_body" to "対応チームに通知しました。その場を離れないでください。一人ではありません。",
            "dismiss" to "閉じる"
        ),
        "ko" to mapOf(
            "confirm_prompt" to "긴급한 말이 들렸습니다. 지금 바로 도움이 필요하신가요?",
            "confirm_title" to "긴급 도움이 필요하신가요?",
            "confirm_yes" to "예 — 도움 요청",
            "confirm_no" to "아니오 — 취소",
            "activated" to "도움이 오고 있습니다. 대응팀이 귀하의 위치를 통보받았습니다. 그 자리에 계세요. 혼자가 아닙니다.",
            "active_title" to "도움이 오고 있습니다",
            "active_body" to "대응팀이 통보를 받았습니다. 그 자리에 계세요. 혼자가 아닙니다.",
            "dismiss" to "닫기"
        )
    )
}
