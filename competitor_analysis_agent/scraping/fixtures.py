"""Canned data used by MockScraper and MockLLMClient in dry-run mode.

None of this is real -- it's a fictional "personal finance app" competitor
set, shaped exactly like what the real scrapers/LLM would produce, so the
full 5-step pipeline can be exercised end-to-end without credentials.
"""

from __future__ import annotations

from competitor_analysis_agent.models import Competitor, PricingDataPoint, RawComplaintText, RawContentItem

MOCK_COMPETITORS: list[Competitor] = [
    Competitor(
        name="BudgetWise",
        website="https://budgetwise.com",
        continent="North America",
        country="United States",
        category="personal finance app",
    ),
    Competitor(
        name="MoneyMate EU",
        website="https://moneymate.de",
        continent="Europe",
        country="Germany",
        category="personal finance app",
    ),
    Competitor(
        name="AhorraYa",
        website="https://ahorraya.mx",
        continent="South America",
        country="Mexico",
        category="personal finance app",
    ),
    Competitor(
        name="PoupeFacil",
        website="https://poupefacil.com.br",
        continent="South America",
        country="Brazil",
        category="budgeting tool",
    ),
]

MOCK_COMPLAINTS: list[RawComplaintText] = [
    RawComplaintText(
        competitor_name="BudgetWise",
        source="Trustpilot",
        raw_text="The onboarding is way too long and the app crashes every time I try to link a second bank account.",
    ),
    RawComplaintText(
        competitor_name="BudgetWise",
        source="Reddit",
        raw_text="Hidden fees on the premium tier, they don't disclose the annual price upfront.",
    ),
    RawComplaintText(
        competitor_name="AhorraYa",
        source="Google Reviews",
        raw_text="No customer support in Spanish outside business hours, and no way to export your data to Excel.",
    ),
    RawComplaintText(
        competitor_name="PoupeFacil",
        source="App Store",
        raw_text="Doesn't support shared/family budgets, only single-user accounts.",
    ),
]

MOCK_PRICING: list[PricingDataPoint] = [
    PricingDataPoint(competitor_name="BudgetWise", price=9.99, currency="USD", plan_name="Pro"),
    PricingDataPoint(competitor_name="MoneyMate EU", price=14.99, currency="USD", plan_name="Premium"),
    PricingDataPoint(competitor_name="AhorraYa", price=6.99, currency="USD", plan_name="Plus"),
    PricingDataPoint(competitor_name="PoupeFacil", price=7.99, currency="USD", plan_name="Standard"),
]

MOCK_CONTENT: list[RawContentItem] = [
    RawContentItem(
        competitor_name="BudgetWise",
        platform="TikTok",
        content_url="https://tiktok.com/@budgetwise/video/123",
        raw_text_or_transcript=(
            "POV: you check your bank account after payday. [screen recording of app auto-categorizing "
            "spending] 3 signs you're about to overspend this month, save this before Friday."
        ),
        engagement_note="engagement=1200000",
    ),
    RawContentItem(
        competitor_name="AhorraYa",
        platform="Instagram",
        content_url="https://instagram.com/reel/ahorraya123",
        raw_text_or_transcript=(
            "Nadie me enseño esto sobre el dinero. [text overlay] 3 errores que cometes con tus ahorros "
            "sin darte cuenta. Guarda este video."
        ),
        engagement_note="engagement=340000",
    ),
]

MOCK_LLM_RESPONSES: dict[str, dict] = {
    # keywords stay English (real search-query language, see llm/prompts.py);
    # competitor_categories and every other field below are Turkish, matching
    # what the real Gemini calls are instructed to produce in live mode.
    "KeywordsAndCategories": {
        "keywords": [
            "personal finance app",
            "budgeting app",
            "expense tracker",
            "savings app",
            "money management app",
            "financial planning tool",
            "spending tracker app",
        ],
        "competitor_categories": [
            "bütçeleme uygulamaları",
            "gider takip uygulamaları",
            "tasarruf ve hedef uygulamaları",
            "neobank finans özellikleri",
        ],
    },
    "Step2LLMOutput": {
        "recommended_continent": "Güney Amerika",
        "candidate_countries": [
            {"country": "Mexico", "rationale": "Akıllı telefon kullanımının yaygın olduğu, fintech benimsemenin hızla büyüdüğü ve yalnızca bir yerleşik yerel rakibin bulunduğu büyük bir nüfus."},
            {"country": "Brazil", "rationale": "En büyük LATAM ekonomisi, güçlü fintech kültürü (Pix) ve dağınık/parçalı bütçeleme uygulaması pazarı."},
            {"country": "Argentina", "rationale": "Enflasyon kaynaklı yüksek finansal kaygı, bütçeleme araçlarına güçlü talep yaratıyor."},
            {"country": "Colombia", "rationale": "Artan dijital bankacılık penetrasyonu ve bu kategoride düşük rakip yoğunluğu."},
            {"country": "Peru", "rationale": "Az sayıda özel bütçeleme uygulamasının bulunduğu gelişmekte olan bir fintech pazarı."},
        ],
    },
    "Step3LLMOutput": {
        "recommended_entry_price": 7.49,
        "rationale": (
            "Gözlemlenen ortalamanın ($9.99) hemen altında ve en ucuz rakip olan AhorraYa'ya ($6.99) yakın "
            "konumlandırıldı; hedef LATAM ülkeleri üst-orta gelir düzeyinde ve fiyata duyarlı olduğundan girişte "
            "rekabetçi kalınıyor, ileride daha yüksek bir katman sunmak için de alan bırakılıyor."
        ),
    },
    "Step4LLMOutput": {
        "strategic_value_adds": [
            {
                "competitor_weakness": "Banka hesabı bağlarken uzun süren ve sık sık çöken katılım akışı (BudgetWise).",
                "recommended_feature": "Otomatik yeniden deneme ve ilerleme kaydı içeren, tek dokunuşla tamamlanan, kaldığı yerden devam edebilen banka bağlama akışı.",
            },
            {
                "competitor_weakness": "Gizli/açıklanmamış premium fiyatlandırma (BudgetWise); veri dışa aktarma imkânı yok (AhorraYa).",
                "recommended_feature": "Kayıt öncesi net şekilde gösterilen yıllık fiyatlandırma ve tüm katmanlarda tek tıkla CSV/Excel dışa aktarma.",
            },
            {
                "competitor_weakness": "Ortak/aile bütçesi desteği yok (PoupeFacil); mesai saatleri dışında yerel dilde destek yok (AhorraYa).",
                "recommended_feature": "Haneler için yerleşik ortak bütçe modu ve 7/24 erişilebilir İspanyolca/Portekizce destek sohbet botu.",
            },
        ]
    },
    "Step5LLMOutput": {
        "hook_analysis": "Gerçek bir uygulama ekran kaydı üzerine bindirilmiş, tanıdık bir POV metin kancasıyla açılıyor ve evrensel bir maaş günü kaygısını adlandırarak ilk saniyede kaydırmayı durduruyor.",
        "intro_and_problem": "Problemi görünmez bir örüntü olarak çerçeveliyor ('fazla harcamak üzere olduğunuzun 3 işareti'), izleyicinin çözülmesini istediği bir merak boşluğu yaratıyor.",
        "body_and_value": "Uygulamanın otomatik kategorilendirme özelliğini canlı olarak gösteriyor, her 'işareti' somut bir uygulama içi ekranla ilişkilendirerek ürünün kendisini değerin kanıtı hâline getiriyor.",
        "call_to_action": "Aciliyet hissi yaratan bir kaydetme çağrısıyla kapanıyor ('Cuma'dan önce bunu kaydet'), dikkati sadece beğeniye değil kaydetme/paylaşma eylemine dönüştürüyor.",
        "overall_summary": "İşe yarıyor çünkü hissedilen bir duyguyu (maaş günü kaygısı) doğal olarak kaydedilebilir bir kontrol listesi formatına dönüştürüyor ve ürün arayüzünü satış havasında olmayan, organik bir kanıt olarak kullanıyor.",
    },
    "Step6LLMOutput": {
        "tier1_ayna": {
            "hook": "Aynı POV ekran kaydı kancası, kendi uygulama arayüzümüzle yeniden çekilir; metin stili ve zamanlama birebir korunur.",
            "intro": "Aynı 'fazla harcamak üzere olduğunuzun 3 işareti' merak boşluğu, marka renklerimizle güncellenmiş metin overlay'i.",
            "body": "Aynı otomatik kategorilendirme gösterimi, kendi uygulama ekranlarımızla birebir aynı akışta.",
            "cta": "Aynı 'Cuma'dan önce kaydet' çağrısı, kendi marka adımızla.",
        },
        "tier2_hibrit": {
            "hook": "Aynı maaş günü kaygısı kancası, ek olarak 've nasıl önleneceği' vaadini de baştan ekleriz.",
            "intro": "Aynı 3 işaret çerçevesi, üzerine bizim ortak bütçe modumuzun farkını vurgulayan bir cümle eklenir.",
            "body": "Otomatik kategorilendirmeyi gösteririz, ardından rakipte olmayan aile/ortak bütçe özelliğimizi ekstra değer olarak sergileriz.",
            "cta": "Kaydetme çağrısına ek olarak ücretsiz deneme bağlantısı eklenir.",
        },
        "tier3_ozgun": {
            "hook": "Tamamen farklı bir açılış: gerçek bir kullanıcı itirafı formatında, kendi sesimizle yazılmış özgün bir kanca.",
            "intro": "Aynı duygu (maaş günü kaygısı) ama sıfırdan kurgulanmış, kendi anlatım dilimizle bir hikaye çerçevesi.",
            "body": "Ürünümüzün otomatik kategorilendirme ve ortak bütçe özelliklerini kendi özgün örnek senaryomuzla anlatırız.",
            "cta": "Kendi marka sesimizle yazılmış, özgün bir kaydetme/takip çağrısı.",
        },
        "concept_summary": (
            "Maaş günü kaygısını uygulamanın otomatik kategorilendirme özelliğiyle çözen, "
            "kaydedilebilir bir 'uyarı işaretleri' formatındaki bütçe farkındalığı içeriği."
        ),
    },
}
