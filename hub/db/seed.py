import time
from sqlalchemy.orm import Session
from hub.db.schema import SystemVersion, EvacInfo, KBArticle, Category, Hub


def seed_data(db: Session):
    # 1. Ensure SystemVersion exists (replaces KBMeta)
    sv = db.query(SystemVersion).filter(SystemVersion.id == 1).first()
    if not sv:
        sv = SystemVersion(id=1, kb_version=1, last_published=int(time.time()))
        db.add(sv)
        print("Seeded SystemVersion.")

    # 2. Seed default message categories
    if db.query(Category).count() == 0:
        defaults = [
            ("Resource Request", "Request supplies, equipment, or personnel from another hub"),
            ("Medical Alert", "Medical emergency or health-related communication"),
            ("Status Update", "General status report from a hub"),
            ("Evacuation Notice", "Evacuation orders or relocation instructions"),
            ("General Communication", "General inter-hub messages"),
        ]
        for name, desc in defaults:
            db.add(Category(category_name=name, description=desc))
        print("Seeded message categories.")

    # 3. Ensure this hub exists in the hub table
    if db.query(Hub).count() == 0:
        db.add(Hub(hub_name="This Hub", location="Local", created_at=int(time.time())))
        print("Seeded default hub entry.")

    # 4. Ensure EvacInfo row exists (replaces StructuredConfig defaults)
    evac = db.query(EvacInfo).filter(EvacInfo.id == 1).first()
    if not evac:
        evac = EvacInfo(
            id=1,
            food_schedule="Morning: 08:00, Lunch: 12:00, Dinner: 18:00",
            sleeping_zones="Zone A, Zone B",
            medical_station="Room 101",
            registration_steps="Step 1: Go to desk. Step 2: Show ID.",
            announcements="",
            emergency_mode="false",
            last_updated="",
            info_metadata="{}",
        )
        db.add(evac)
        print("Seeded EvacInfo.")

    # 3. Seed a welcome KB article if the table is empty
    if db.query(KBArticle).count() == 0:
        now = int(time.time())
        article = KBArticle(
            question="Welcome",
            answer="Welcome to the Evacuation Center. Please register at the front desk.",
            category="general",
            tags="welcome,start",
            enabled=1,
            source="seed",
            created_at=now,
            last_updated=now,
        )
        db.add(article)
        print("Seeded welcome article.")

    db.commit()

    # Sync evac_info fields → KB articles for semantic search
    from hub.db.evac_sync import sync_evac_to_kb
    sync_evac_to_kb(db)

    # Enrich tags for core KB articles with multilingual synonyms
    _enrich_multilingual_tags(db)


def _enrich_multilingual_tags(db: Session):
    """Add multilingual tags to core KB articles to improve non-English recall."""
    from hub.db.schema import KBArticle
    from hub.retrieval.embedder import load_embedder, serialize_embedding, get_embeddable_text
    from hub.retrieval.search import invalidate_corpus_cache
    import time as _time

    tag_map = {
        "where can i wash my clothes?": [
            "laundry", "wash", "clothes",
            "lavanderia", "area de lavado", "lavar la ropa",
            "waschraum", "wasche", "waschebereich",
            "blanchisserie", "zone de lavage", "laver les vetements",
            "洗濯", "洗濯場所", "洗濯エリア",
        ],
        "what is the food schedule?": [
            "food", "meals", "schedule",
            "food distribution", "food distribution schedule", "food distribution time",
            "meal distribution", "meal distribution schedule",
            "comida", "horario de comidas",
            "essen", "essenszeit",
            "repas", "horaire des repas",
            "食事", "食事時間",
        ],
        "where are the sleeping zones?": [
            "sleeping", "beds", "cots",
            "zona de dormir", "camas",
            "schlafbereich", "betten",
            "zone de sommeil", "lits",
            "寝る場所", "寝室", "ベッド",
        ],
        "where is the medical station?": [
            "medical", "clinic", "doctor", "nurse",
            "medico", "clinica",
            "arzt", "klinik",
            "medical", "clinique",
            "医療", "診療所",
        ],
        "how do i register?": [
            "registration", "sign up", "check in",
            "registro", "inscribirme",
            "registrierung", "anmeldung",
            "inscription", "enregistrer",
            "登録", "受付",
        ],
    }

    updated = []
    for art in db.query(KBArticle).all():
        q = (art.question or "").strip().lower()
        if q in tag_map:
            existing = set(t.strip() for t in (art.tags or "").split(",") if t.strip())
            new_tags = [t for t in tag_map[q] if t and t not in existing]
            if new_tags:
                art.tags = ",".join(list(existing) + new_tags)
                art.last_updated = int(_time.time())
                art.embedding = None
                updated.append(art)

    if not updated:
        return

    # Re-embed updated articles
    embedder = None
    try:
        embedder = load_embedder()
    except Exception:
        embedder = None
    for art in updated:
        try:
            if embedder:
                text = get_embeddable_text(art)
                vec = embedder.embed_text(text)
                art.embedding = serialize_embedding(vec)
            else:
                art.embedding = None
        except Exception:
            # Leave embedding None; startup will attempt to fill missing
            art.embedding = None

    db.commit()
    invalidate_corpus_cache()
