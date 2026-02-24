"""
Prototype-based intent classifier using the same MiniLM embedder as semantic search.
Used to enrich queries before retrieval and to gate clarification (only when intent is unclear).
"""
import numpy as np
from typing import Tuple, List, Dict

# 18 intents for evacuation-center kiosk (excluding "unclear", which is returned when confidence < 0.30)
INTENT_LABELS: List[str] = [
    "greeting",
    "identity",
    "capability",
    "small_talk",
    "food",
    "medical",
    "registration",
    "sleeping",
    "transportation",
    "safety",
    "facilities",
    "lost_person",
    "pets",
    "donations",
    "hours",
    "location",
    "general_info",
    "goodbye",
    "inventory",
]

INTENT_PROTOTYPES: Dict[str, List[str]] = {
    "greeting": [
        "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
        "howdy", "hi there", "hello there", "greetings", "hallo",
    ],
    "identity": [
        "who are you", "what are you", "what is this", "what is this kiosk",
        "are you a robot", "are you human", "what is reskiosk",
    ],
    "capability": [
        "what can you do", "what can you help with", "how can you help",
        "what information do you have", "what do you know", "can you help me",
    ],
    "small_talk": [
        "how are you", "how is it going", "nice day", "thank you", "thanks",
        "okay", "alright", "got it", "I see",
    ],
    "food": [
        "where is food", "when is lunch", "when is dinner", "meal times",
        "where do we eat", "food schedule", "breakfast hours", "where can I get food",
        "is there food", "meal distribution", "feeding times", "cafeteria",
    ],
    "medical": [
        "I need a doctor", "medical help", "where is the nurse", "I feel sick",
        "medical assistance", "first aid", "where is medical", "health services",
        "I need medicine", "medical tent", "doctor", "nurse",
    ],
    "registration": [
        "how do I register", "where do I sign in", "registration desk",
        "check in", "sign up", "register my family", "registration process",
        "where to register", "get registered", "intake",
    ],
    "sleeping": [
        "where do I sleep", "sleeping area", "where can I sleep", "beds",
        "sleeping quarters", "cots", "rest area", "where to sleep",
        "sleeping arrangements", "overnight",
    ],
    "transportation": [
        "how do I leave", "bus schedule", "when is the bus", "transportation",
        "ride", "shuttle", "how to get out", "when can I leave",
        "bus to town", "transport", "pickup",
    ],
    "safety": [
        "is it safe", "emergency", "evacuation", "where to go in emergency",
        "safety", "fire exit", "emergency exit", "what if there is a fire",
    ],
    "facilities": [
        "where is the bathroom", "restroom", "toilet", "showers",
        "laundry", "charging station", "phone charging", "wi-fi",
        "bathroom", "washroom", "where can I shower",
    ],
    "lost_person": [
        "I lost my family", "missing person", "lost my child", "find my family",
        "reunification", "lost and found", "where is my husband", "missing child",
    ],
    "pets": [
        "can I bring my dog", "pets allowed", "where do I put my pet",
        "animal", "dog", "cat", "pet area", "pet shelter",
    ],
    "donations": [
        "where do I donate", "how to donate", "donation center",
        "I want to donate", "accepting donations", "drop off donations",
    ],
    "hours": [
        "what time do you open", "when do you close", "hours of operation",
        "opening hours", "when is the desk open", "what time",
    ],
    "location": [
        "where am I", "address", "where is this place", "how do I get here",
        "directions", "what is this building", "where is the center",
    ],
    "general_info": [
        "what services are available", "what do you offer", "general information",
        "tell me about the center", "what is available", "help",
        "I need help", "I have a question", "information",
    ],
    "goodbye": [
        "bye", "goodbye", "see you", "thank you goodbye", "that's all",
        "nothing else", "done", "that's it",
    ],
    "inventory": [
        "what supplies are available", "is there food", "do you have water",
        "are there blankets available", "what do you have here",
        "is medicine available", "are there hygiene kits", "inventory status",
        "is there clothing", "are there diapers", "are charging ports available",
        "are there cots", "what can i get", "supply levels", "what is available",
        "may pagkain ba", "may gamot ba", "may tubig ba",
        "hay comida", "hay agua", "hay medicamentos",
    ],
}

UNCLEAR_THRESHOLD = 0.30


class IntentClassifier:
    """
    Classifies user queries into one of INTENT_LABELS using prototype phrase embeddings.
    Centroids are computed at init; classify() returns (intent, score), or ("unclear", score) if best_score < 0.30.
    """

    def __init__(self, embedder):
        self.embedder = embedder
        self._centroids: Dict[str, np.ndarray] = {}
        self._build_centroids()

    def _build_centroids(self) -> None:
        all_phrases = []
        intent_index = []  # which intent each phrase belongs to
        for intent in INTENT_LABELS:
            phrases = INTENT_PROTOTYPES.get(intent, [])
            for _ in phrases:
                intent_index.append(intent)
            all_phrases.extend(phrases)

        if not all_phrases:
            return

        # Batch embed all prototypes
        embeddings = self.embedder.embed_text(all_phrases)
        if isinstance(embeddings, np.ndarray) and embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        # Average per intent and L2-normalize
        for intent in INTENT_LABELS:
            indices = [i for i, intent_name in enumerate(intent_index) if intent_name == intent]
            if not indices:
                continue
            vecs = embeddings[indices]
            centroid = np.mean(vecs, axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            self._centroids[intent] = centroid.astype(np.float32)

    def classify(self, query: str) -> Tuple[str, float]:
        """
        Returns (best_intent, best_score). If best_score < UNCLEAR_THRESHOLD, returns ("unclear", best_score).
        """
        if not self._centroids:
            return ("unclear", 0.0)

        q_vec = self.embedder.embed_text(query.strip())
        if isinstance(q_vec, np.ndarray) and q_vec.ndim > 1:
            q_vec = q_vec[0]
        q_norm = np.linalg.norm(q_vec)
        if q_norm <= 0:
            return ("unclear", 0.0)
        q_vec = (q_vec / q_norm).astype(np.float32)

        best_intent = "unclear"
        best_score = -1.0
        for intent, centroid in self._centroids.items():
            score = float(np.dot(q_vec, centroid))
            if score > best_score:
                best_score = score
                best_intent = intent

        if best_score < UNCLEAR_THRESHOLD:
            return ("unclear", best_score)
        return (best_intent, best_score)
