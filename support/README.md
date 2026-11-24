# QueuePilot kaynaklı çözüm önerisi

## Hızlı başlangıç

Komutları repository kökünde, QueuePilot’un mevcut Python ortamında çalıştırın. Arayüz için doğrulanmış bir sınıflandırma modeli gerekir. Evaluator sınıflandırıcıdan bağımsız çalışır.

```powershell
python -m app.resolution.index index --output .checks/support-index.json
$env:SUGGEST_INDEX = ".checks/support-index.json"
$env:SUGGEST_DB = ".checks/support-operations.sqlite3"
$env:SUGGEST_PROVIDER = "fake"
$env:MODEL_BACKEND = "baseline"
python -m uvicorn app.main:app
```

Arayüzü `http://127.0.0.1:8000/` adresinde açın ve **Classify ticket** ile bir ticket sınıflandırın. Sonuç manuel inceleme gerektiriyorsa panelde **Suggest resolution** görünür. Düğmeye bastığınızda taslağı ve pasaj kimliğini veya taslak bulunamadığına dair kısa bir mesaj görürsünüz. Aşağıdaki API örneği, sınıflandırıcının kararından bağımsız olarak VPN taslağını denemenizi sağlar.

```powershell
$headers = @{ "Idempotency-Key" = [guid]::NewGuid().ToString() }
if ($env:API_KEY) { $headers["X-API-Key"] = $env:API_KEY }
$body = @{ text = "The VPN client reports an expired profile." } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/suggest-resolution -Method Post `
  -Headers $headers -ContentType "application/json" -Body $body
python -m scripts.evaluate_resolution --index .checks/support-index.json --split final --output .checks/support-final.json
```

API `operation_id`, `status`, `review_reason`, `draft`, `sources` ve süre bilgilerini döndürür. `draft_ready` durumunda kaynaklar pasaj ve doküman kimliğini, başlığı, bölümü ve varsa bağlantıyı içerir. `needs_review` ve `in_progress` durumlarında taslak ve kaynak listesi boştur. İş sonuçlarında HTTP 200, hatalı yetkide 401, aynı anahtarla farklı içerikte 409, geçersiz girdide 422 ve özellik kapalı veya SQLite erişilemiyorsa 503 döner. Anahtar 1–128 karakterdir ve ASCII harf, rakam, nokta, alt çizgi, tilde veya kısa çizgi içerebilir. Ticket en fazla 5.000 karakterdir.

## Yapılandırma

| Değişken | Kullanım |
| --- | --- |
| `SUGGEST_PROVIDER` | Boşsa özellik kapalıdır. `fake` ilk seçilen pasajı aktaran deterministik offline demo, `openai` harici üretim adapter’ıdır. |
| `SUGGEST_INDEX` | İndeksleme komutunun oluşturduğu JSON dosyası. |
| `SUGGEST_DB` | SQLite dosyası. Üst dizin yazılabilir olmalıdır. Birden çok worker aynı yerel dosyayı kullanır. |
| `SUGGEST_RETRIEVER` | Varsayılan `lexical`. `dense` için vektörlü indeks ve model cache’i gerekir. |
| `API_KEY` | Mevcut `X-API-Key` doğrulaması. Harici sağlayıcı için API açılmadan önce ayarlanması gerekir. |
| `SUGGEST_OPENAI_MODEL` | Chat Completions üzerinde strict JSON Schema destekleyen model kimliği. Tekrar üretim için tarihli bir model sürümü kullanın. |
| `SUGGEST_OPENAI_API_KEY` | Harici sağlayıcının erişim anahtarı. |

Dense seçenek aynı pasajların 384 boyutlu normalize edilmiş vektörlerini saklar ve CPU’da tam kosinüs benzerliğiyle sıralar. Model ve revizyon sabittir. `HF_HOME` kullanıyorsanız kurulum, indeksleme ve API’de aynı cache konumunu kullanın. Ağ erişimi yalnızca açık `download-model` adımında gerekir. İndeksleme ve çalışma zamanı modeli `local_files_only=True` ile yükler. [Sabit model revizyonu](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/tree/e8f8c211226b894fcb81acc59f3b34ba3efd5f42)

```powershell
python -m pip install -r requirements/suggestion/dense.txt
python -m app.resolution.index download-model
$env:HF_HUB_OFFLINE = "1"
python -m app.resolution.index index --dense --output .checks/support-dense.json
$env:SUGGEST_INDEX = ".checks/support-dense.json"
$env:SUGGEST_RETRIEVER = "dense"
python -m scripts.evaluate_resolution --index .checks/support-dense.json --split final --retrievers lexical dense --output .checks/support-comparison.json
```

Gerçek sağlayıcıyı etkinleştirmek için önce ulaşım profilini kurun. Dev profili zaten aynı HTTP istemcisini içerir. HTTPX, model isteğinin süre dolduğunda iptal edilebilmesini sağlar. Dense bağımlılıkları ayrı profildedir. Varsayılan API profili aynı kalır.

```powershell
python -m pip install --require-hashes -r requirements/suggestion/provider.txt
$env:SUGGEST_PROVIDER = "openai"
# API_KEY ve SUGGEST_OPENAI_API_KEY değerlerini ortamınıza güvenli şekilde yükleyin.
$env:SUGGEST_OPENAI_MODEL = "<structured-output-model-id>"
python -m uvicorn app.main:app
```

OpenAI isteğinde sabit sistem prompt’u ve yapılandırılmış çıktı şemasıyla birlikte ticket metni ve seçilen pasajların metni, başlığı, bölümü ve kimliği gönderilir. Kaynak bağlantıları ve işlem bilgileri yerelde kalır. Harici istek `store=false` kullanır ve araç tanımlamaz. [Chat Completions API sözleşmesi](https://developers.openai.com/api/reference/resources/chat)

Gerçek model değerlendirmesi ücretli çağrılar yapabilir ve açıkça başlatılır. Sadece repository’deki sentetik örnekleri kullanır. Sağlayıcı kullanım bildirdiğinde raporda giriş/çıkış token toplamları ve kapsanan istek sayısı görünür. Birim fiyatlar ve fiyat kaynağı `--prices INPUT_USD OUTPUT_USD --pricing-source URL` ile sağlanırsa, kullanım kapsamındaki çağrılar için milyon token başına fiyatlardan yaklaşık USD tutarı hesaplanır.

```powershell
python -m scripts.evaluate_resolution --index .checks/support-index.json --split final --provider openai --output .checks/support-openai-final.json
```

## Tasarım ve veri

- **Corpus ve indeks.** [Corpus](corpus/) QueuePilot için yazılmış özgün, sentetik Türkçe ve İngilizce prosedürlerden oluşur. `import-example.md` bir dokümana gömülmüş talimat örneğidir. Her Markdown dosyasının adı doküman kimliğidir. H1 başlıktır, isteğe bağlı `Source: https://…` satırı bağlantıdır ve her H2 başlığı `[bölüm-kimliği]` ile başlar. Her paragraf tek pasajdır. Bu boyuttaki prosedürler paragraf halinde okunabildiği için adımlar bir arada kalır, farklı bölümler birbirine karışmaz. Paragraf sınırı 1.000 karakterdir. Pasaj kimliği `doküman:bölüm:paragraf-sırası` biçimindedir. Bir bölüme paragraf eklerken mevcut kimlikleri korumak için sona ekleyin veya yeni bölüm açın. İndeksleme çıktıyı atomik olarak değiştirir. Corpus hash’i chunking sürümü ve pasajları kapsar. Vektörlü indeks ayrıca sabit embedding revizyonunu kaydeder.
- **Arama ve kanıt kapısı.** BM25 ve dense aynı pasajları sıralar. Servis ilk üç aday arasından, Türkçe karakter normalizasyonu ve stopword temizliğinden sonra ticket ile en az iki farklı terimi ortak olan pasajları seçer. Modele verilecek pasaj dizisi JSON olarak en fazla 3.500 karakterdir. Ortak terim kuralı geliştirme örnekleriyle kontrol edildi ve iki yöntemde aynıdır. Kural konu örtüşmesi için kaba bir kapıdır. Eşanlamlıları kaçırabilir ve farklı bir niyeti aynı konuyla eşleştirebilir. BM25 ve kosinüs skorları sadece kendi sıralamalarında kullanılır.
- **Üretim ve inceleme.** Arayüz öneri düğmesini mevcut manuel inceleme sonucunda gösterir. İstemci ticket’ı açık bir operatör eylemiyle gönderir. Retrieval ve kanıt kapısı geçilirse sağlayıcı taslak ve pasaj kimlikleri döndürür. Servis formatı, boş veya tekrarlı atıfları ve kimliklerin seçilen pasajlara ait olup olmadığını kontrol eder. Kaynak başlıkları ve bağlantıları indeksten gelir. Operatör taslağı değerlendirir ve destek sürecinde ne yapacağına karar verir. Uygulamada müşteri gönderimi ve ticket değiştirme yetkisi bulunmaz. Geçerli kimlikler taslağın anlam bakımından kaynakla desteklendiğini tek başına kanıtlayamaz.
- **Süre ve iş sonuçları.** Uygulama işlem bütçesi 10 saniyedir. Sonuç yazımı için 1 saniye ayrılır. Sağlayıcıya en fazla 7 saniye ve her işlemde bir çağrı verilir. SQLite kilit bekleme üst sınırı bağlantı başına 250 ms’dir. Native dense hesaplama iptal edilirse arka planda tamamlanabilir. Dense arama yuvası bu süre boyunca dolu kalır. İnceleme kodları `insufficient_evidence`, `provider_abstained`, `provider_timeout`, `provider_error`, `invalid_output`, `request_timeout`, `retrieval_unavailable` ve `interrupted` değerleridir. `in_progress` aynı anahtarla tekrar sorgulanabilir.
- **SQLite ve tekrar.** Benzersizlik kısıtı yetki kapsamı hash’i ile idempotency anahtarı üzerindedir. Tek API anahtarı tek ortak kapsam oluşturur. Anahtarsız demo tek anonim kapsam kullanır. Ticket’ın doğrulama sonrası SHA-256 özeti aynı anahtarın farklı içerikle kullanımını saptar. İşlem oluşturma ve sonuç yazma ayrı kısa transaction’lardır. Devam eden işlem 30 saniye sonra aynı girdi tekrar gelirse `interrupted` olarak kapanır. Ağ çağrısının önceki denemede gerçekleşmiş olabileceği varsayılır ve aynı anahtar altında tekrar yapılmaz. Yeni bir operatör denemesi yeni bir anahtar kullanır.
- **Saklama.** DB işlem kimliğini, idempotency anahtarını, kapsam ve ticket özetlerini, durum ve lease zamanını, corpus ve model/sağlayıcı/prompt ayarlarını, seçilen pasaj kimliklerini ve tekrar sunulan sonucu saklar. Sonuç içinde kabul edilmiş taslak, kaynak metaverisi, kodlar, süreler ve varsa token sayıları bulunur. Taslak sağlayıcının tekrar ettiği ticket parçaları içerebilir. API ham ticket’ı ayrı bir depoya veya loga yazmaz. DB dosyasına erişimi sınırlandırın ve saklama süresi sonunda dosyayı işletim politikanıza göre güvenle silin. Otomatik veri temizleme uygulanmaz.
- **Dağıtım sınırı.** Tek servis, yerel indeks ve SQLite, küçük koleksiyon ve operatörün hemen sonuç almasının yeterli olduğu etkileşimli demo için kullanılır. Birden çok sunucuda aynı işlemleri paylaşma ihtiyacı, beklemeye gelmeyen sağlayıcı gecikmesi veya yoğun eşzamanlılıkta ölçülen kilit ve arama darboğazı kuyruk ve paylaşılan saklamayı gündeme getirir. Corpus belleği, indeks yükleme süresi veya ölçülen arama p95’i hedefi aştığında harici indeks değerlendirilebilir.

[Çalıştırılan değerlendirme ve gözlemler](evaluation/RESULTS.md)
