# competitor_analysis_agent

`CLAUDE.md`'de tanımlanan otonom Rakip ve Pazar Analizi Ajanı'nın Python implementasyonu.

## Kurulum

```bash
pip install -r requirements.txt
playwright install chromium   # sadece canlı (--live) scraping için gerekli
copy .env.example .env        # sonra .env içine gerçek anahtarları gir
```

`.env` içindeki değişkenler için `.env.example` dosyasındaki yorumlara bakın.
`SUPABASE_KEY` **service_role** anahtarı olmalı (anon değil) — şemada RLS
policy yok ve ajan sunucu tarafında kimliksiz çalışıyor.

## Çalışma modları

Ajan iki modda çalışır:

- **dry-run (mock)**: Gerçek API anahtarı gerektirmez. Sahte LLM ve scraping
  verisiyle 5 adımlık akışı uçtan uca çalıştırır, sonucu `./output/*.json`
  dosyalarına yazar. `SUPABASE_URL`/`GEMINI_API_KEY`/`APIFY_API_TOKEN`
  eksikse otomatik olarak bu moda düşer; `--dry-run` ile zorlanabilir.
- **live**: `.env` içinde tüm gerçek anahtarlar varsa `--live` ile gerçek
  Gemini/Apify/Playwright/Supabase çağrıları yapılır. Live modda tüm
  scraping+LLM adımları bitip Supabase'e kayıt başarısız olursa (örn.
  `SUPABASE_URL` çözümlenmiyor/proje duraklatılmış), sonuçlar kaybolmaz --
  otomatik olarak `./output/projects/<id>.json` altına yerel yedek yazılır;
  Supabase bağlantısını düzelttikten sonra bu dosyadan elle aktarabilirsiniz.

## Supabase tablolarını oluşturma

```bash
python -m competitor_analysis_agent.db.setup_db
```

`SUPABASE_DB_URL` (Project Settings > Database > Connection string, "Session"
modu) `.env` içinde tanımlıysa tablolar doğrudan oluşturulur. Tanımlı
değilse, komut `competitor_analysis_agent/db/schema.sql` içeriğini ekrana
basar — bunu Supabase Dashboard > SQL Editor'e yapıştırıp çalıştırın.

**Şema notu (seçmeli modül çalıştırma + içerik iskeleti geçmişi):**
`market_and_gap_analysis`'a `project_description` ve `modules_run` eklendi;
coğrafi/fiyat/gap kolonları artık nullable (bir çalıştırmada seçilmeyen
modül için `NULL` kalır). `viral_contents`'e `project_id` eklendi ve yeni
`content_skeletons` tablosu (Tier 1/2/3 = Ayna/Hibrit/Özgün içerik
iskeletleri) tanımlandı. `CREATE TABLE IF NOT EXISTS` var olan bir tabloyu
değiştirmez, sadece eksikse oluşturur -- bu şemadan önce oluşturulmuş bir
Supabase projeniz varsa (yani `setup_db.py` bu güncellemeden önce en az bir
kez çalıştırılmışsa), tabloları silmeden şu ek migration'ı uygulayın (sadece
`ADD COLUMN`/kısıtlama gevşetme, veri kaybı riski yok):

```bash
# SUPABASE_DB_URL .env içinde tanımlıysa doğrudan uygulanır, değilse
# competitor_analysis_agent/db/migrate_v2_selective_modules.sql içeriğini
# Supabase Dashboard > SQL Editor'e yapıştırıp çalıştırın.
python -c "from competitor_analysis_agent.config import get_settings; import psycopg2; s=get_settings(); c=psycopg2.connect(s.supabase_db_url); c.autocommit=True; c.cursor().execute(open('competitor_analysis_agent/db/migrate_v2_selective_modules.sql', encoding='utf-8').read()); print('applied')"
```

Doğrudan `psycopg2` ile (Supabase'in yönetim API'si yerine) uygulandığından,
PostgREST'in şema önbelleği yeni kolonları hemen görmeyebilir -- birkaç
saniye içinde kendiliğinden yenilenir; hemen denemek isterseniz aynı
bağlantıyla `NOTIFY pgrst, 'reload schema';` çalıştırın.

## Çalıştırma

```bash
# Anahtar yokken / test amaçlı (mock veriyle, output/*.json üretir)
python -m competitor_analysis_agent.main --project-description "..." --dry-run

# Gerçek anahtarlarla (Supabase'e gerçek insert yapar)
python -m competitor_analysis_agent.main --project-description "..." --live
```

## Testler

```bash
pytest tests/
```

`test_pricing.py` ve `test_geo_filter.py` ağ gerektirmeyen saf mantık
testleridir. `test_orchestrator_dry_run.py` tüm 5 adımı mock modda uçtan uca
çalıştırıp çıktının üç Supabase tablosunun (market_and_gap_analysis,
viral_contents, content_skeletons) şemasına uyduğunu doğrular.
`test_orchestrator_module_selection.py` seçmeli modül çalıştırmayı (sadece
işaretlenen modülün scraping tetiklediğini) ve etkileşim-bazlı içerik
filtresini, `test_step6_content_tiering.py` Tier 1/2/3 üretimini,
`test_repository_history.py` geçmiş projeler listesi/detayı ve
biriktirme (append) davranışını doğrular.

## Masaüstü Web Arayüzü (GUI)

Çekirdek ajan mantığı (`orchestrator.py` ve altındaki tüm adımlar/scraping/
LLM/Supabase entegrasyonu) hiç değişmeden, aynı `run_pipeline`'ı yerel bir
tarayıcı arayüzünden tetikleyen bir FastAPI sunucusu (`competitor_analysis_agent/gui/`)
eklenmiştir.

**Geliştirme modunda çalıştırma** (derlemeden):

```bash
python run_app.py
# veya çift tıkla: run_gui.bat
```

`http://127.0.0.1:8756/` adresini otomatik olarak varsayılan tarayıcıda açar.
Formdan proje açıklamasını girip Dry-Run veya Live Run modunu seçin; canlı
loglar ve sonuçlar (fiyat matrisi, ilk 3 ülke, stratejik öneriler, viral
içerik anatomisi) aynı sayfada akar/görüntülenir.

**Seçmeli modül çalıştırma:** Formda 4 checkbox var (Pazar Analizi, Fiyatlandırma,
Tutan İçerik İskeletleri, Ekstra Özellik & Fırsat Analizi) -- sadece
işaretlenen modüller için scraping/LLM çağrısı yapılır, token/kredi
harcanmaz. "Tutan İçerik İskeletleri" işaretlenince kaç rakip içeriği
inceleneceğini soran bir sayı kutusu açılır; en yüksek etkileşimli o kadar
içerik seçilip her biri için Tier 1/2/3 (Ayna/Hibrit/Özgün) içerik iskeleti
üretilir.

**Geçmiş Projelerim:** Üstteki sekmeden geçmişte çalıştırılmış projeler
listelenir (Supabase'den veya dry-run'da `output/projects/*.json`'dan);
bir projeye tıklayınca o projenin tüm sonuçları yüklenir. Proje detayında
"Dinamik Yeni İçerik İskeleti Çıkar" butonuyla, sadece içerik iskeleti
modülü o proje için (kayıtlı proje açıklaması yeniden kullanılarak) istenen
sayıda içerikle tekrar çalıştırılabilir; üretilenler öncekinin üzerine
eklenir, üzerine yazmaz.

Backend endpoint'leri: `POST /api/analyze`, `GET /api/status`,
`GET /api/logs`, `GET /api/results`, `GET /api/projects`,
`GET /api/projects/{id}`, `POST /api/projects/{id}/content-skeletons`.

**Çift tıklanabilir `.exe` üretme:**

```bash
python build_exe.py
```

`dist/Rakip_Analizi_Ajani.exe` üretir. `.env` dosyası exe'nin içine
gömülmez — `dist/.env.example`'ı `dist/.env` olarak kopyalayıp gerçek
anahtarları girin. Dry-run çıktıları ve `.env`, exe'nin bulunduğu klasöre
göre (`output/`, `.env`) okunur/yazılır — CLI ile birebir aynı davranış.

**Masaüstüne kısayol oluşturma:**

`.exe`'yi `dist/` içinde bırakıp masaüstüne bir kısayol oluşturmak (exe'yi
taşımak yerine) önerilir, çünkü `.env` ve `output/` klasörü hep exe'nin
bulunduğu dizine göre çözülür. PowerShell ile:

```powershell
$WshShell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath("Desktop")
$exePath = "<proje_yolu>\dist\Rakip_Analizi_Ajani.exe"
$shortcut = $WshShell.CreateShortcut("$desktop\Rakip Analizi Ajani.lnk")
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = "<proje_yolu>\dist"
$shortcut.Description = "Rakip ve Pazar Analizi Ajani - Masaustu Arayuz"
$shortcut.IconLocation = $exePath
$shortcut.Save()
```

`<proje_yolu>` yerine bu deponun bulunduğu tam yolu yazın (örn.
`C:\Users\<kullanıcı>\Desktop\Rakip_Analizi_Ajani`). Kısayol dosya yoluna
göre çalıştığı için `build_exe.py` her yeniden derlendiğinde (aynı
`dist/Rakip_Analizi_Ajani.exe` yolunu kullanır) kısayolu yeniden
oluşturmaya gerek kalmaz — otomatik olarak güncel `.exe`'yi işaret eder.

Kısayola çift tıklamak arka planda yerel sunucuyu başlatır ve tarayıcıda
`http://127.0.0.1:8756/` adresini açar; uygulamayı kapatmak için sunucuyu
çalıştıran `Rakip_Analizi_Ajani.exe` sürecini (Görev Yöneticisi'nden veya
`Stop-Process -Name Rakip_Analizi_Ajani -Force`) sonlandırın.
