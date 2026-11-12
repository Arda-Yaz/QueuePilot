# Yeni bağımsız veri için hazır doğrulama akışı

Kapsam notu: bu belge ek geliştirme/kuruma uyarlama araştırmasıdır. Mevcut veri kümesinde tamamlanan benchmark sonucunu değiştirmez ve referans uygulamanın tamamlanması için yeni bir zorunluluk tanımlamaz. [Proje kapsamı ve yol haritası](PROJECT_SCOPE.md).

12 Kasım 2026: yeni bağımsız etiketli veri henüz yok. Bu belge ve araçlar bir
doğrulama hazırlığıdır; yeni modelin bağımsız veride başarılı olduğunu göstermez.
Sentetik test sonuçları gerçek veri sonucu olarak kullanılmaz.

## Sabitlenenler

Geliştirme karşılaştırmasındaki referans ve kelime+karakter adayı yeniden
eğitilmeden, hash doğrulamasıyla yerel bir pakete kopyalanır. Paket manifest'i;
model dosyalarını, sınıf şemasını, geliştirme planını/sonucunu, evaluator kaynak
snapshot'ını ve Python/sklearn/numpy/pandas/scipy sürümlerini bağlar. Dosya,
protokol veya evaluator kaynağı değişirse çalıştırma durur. Mevcut üretim
modeli/eşiği değiştirilmez; bu akış otomatik terfi yapamaz.

Risk seçiminde hedef yine 0,90, eşik aralığı 0,10–0,99 ve en az kabul sayısı 50.
İki sabit model karşılaştırılacağı için toplam alpha 0,05 iki modele bölünür;
model başına alpha 0,025 ve 90 eşik için Bonferroni uygulanır. Böylece 180
model/eşik adayı aynı aile içinde ele alınır. Bu, önceki tek modelin geliştirme
ekranından daha muhafazakâr bir gelecek doğrulama protokolüdür.

## İki ayrı yeni veri grubu

1. **Yeni risk verisi:** sabit iki model için eşikleri seçer. Kabul edilenlerde
   doğruluk alt sınırı hedefi karşılamazsa eski eşik veya başka model kullanılarak
   sonuç başarılı gösterilmez. Her iki model için uygun eşik yoksa akış audit'e
   geçmez. Bu bir model arama grubu değildir.
2. **Yeni audit verisi:** eşik seçiminde kullanılmamış başka kayıtlardan oluşur.
   Risk aşamasından gelen eşikler aynen uygulanır. Toplam doğruluk/Macro-F1,
   sınıf sonuçları, coverage ve kabul doğruluğu raporlanır. Sabit iki politika için
   kabul doğruluğunun tek taraflı Clopper-Pearson sınırı alpha 0,025 ile hesaplanır.
   Bu aşamada eşik araması yapılmaz.

Yeni veri grupları değerlendirme başlamadan ayrılmalıdır. Sonuçlar görüldükten
sonra başka kayıtları sırayla ekleyip olumlu sonuç aramak veya örnek sayısını
başarıya göre durdurmak bu protokolün kapsamı değildir.

Audit inceleme ekranı, iki doğruluk kapısının geçmesine ek olarak gözlenen
coverage farkının en az 1 yüzde puanı olmasını, Macro-F1 kaybı olmamasını ve
Administrative rights F1 kaybının en fazla 2 yüzde puanı olmasını kontrol eder.
Sınıfların tümü gözlenmemişse tam ekran geçmez. Coverage farkı ve sınıf F1'leri
nokta tahminleridir; bu ekran artışın istatistiksel olarak kanıtlandığını söylemez.
Sonuç her koşulda insan incelemesi ister; üretim dosyalarına yazılmaz.

## Veri biçimi ve doğruluk kaynağı

CSV şablonu: [`experiments/templates/new_tickets.csv`](../experiments/templates/new_tickets.csv).
Gerekli sütunlar `external_id`, `Document`, `Topic_group`; isteğe bağlı
`labeler_id` ve `label_notes` inceleme izi sağlar. UTF-8 kullanın. Sınıf adları:

- Access
- Administrative rights
- HR Support
- Hardware
- Internal Project
- Miscellaneous
- Purchase
- Storage

Sınıf adları tek başına etiketleme rehberi değildir. Özellikle Administrative
rights gibi anlamı belirsiz görünen gruplarda alan sahibinin kategori tanımını
ve örneklerini doğrulaması gerekir. Yeni etiketler modelin tahmininden
kopyalanmamalı; belirsiz örnekler uzman incelemesinden geçirilmelidir. Burada
etiket taksonomisi uydurulmadı ve değerlendirme etiketleri değiştirilmedi.

Kaynak beyanı şablonu:
[`data_attestation.json`](../experiments/templates/data_attestation.json).
Şablondaki boş alanlar ve `false` değerler bilinçlidir: boş şablon değerlendirmeden
geçemez. Veri sahibinin kaynak, örnekleme yöntemi, etiketleme süreci ve toplama
dönemini açıklaması; daha önce kullanılmadığını ve etiketlerin model tahminlerinden
bağımsız üretildiğini açıkça beyan etmesi gerekir. Beyan doğrulama kanıtı değildir;
araç bunun tarihsel doğruluğunu kendiliğinden bilemez.

İlk kabul kontrolleri boş/eksik alanları, bilinmeyen etiketleri, yinelenen ID'leri,
aynı normalleştirilmiş metni ve eski ham veri kümesiyle metin örtüşmesini reddeder.
Metin hash'i etiketi içermez: eski kaydı yeniden etiketlemek onu yeni yapmaz.
Audit ayrıca risk kayıtlarının metin ve ID'lerini reddeder. Kontrol case/whitespace
farklarını yakalar; paraphrase, aynı biletin farklı sürümleri, e-posta zincirleri
ve gizli geçmiş kullanım için tam bağımsızlık garantisi sağlamaz. Bunlar toplama
ve insan incelemesiyle ele alınmalıdır.

Hedef dağılımı temsil eden rastgele veya ardışık kayıtlar tercih edilmelidir.
Yalnız problemli sınıfı seçmek, tüm biletlerde coverage iddiası için temsilî bir
örneklem oluşturmaz. Eksik sınıflar ve tüm sınıf sayıları sonuçta görünür kalır.

## Örnek sayısı

`min_accepted_samples=50` bir istatistiksel güç planı değildir ve 50 yeni kayıtla
hedefi kanıtlama sözü vermez. İki model/90 eşik düzeltmesi, beklenen hata oranı,
kabul oranı ve sınıf dağılımı ihtiyaç duyulan sayıyı etkiler. Veri kaynağı ve
maliyeti bilindiğinde risk/audit boyutları sonuçlara bakmadan ayrıca planlanmalıdır.
Mevcut veri kümesinden yeni bir bölüm kesmek veya sentetik kayıt üretmek gerçek
yeni bağımsız veri ihtiyacını karşılamaz.

## Çalıştırma

Mevcut development ortamında, repository kökünden:

```powershell
# Yalnız bir kez: mevcut iki modeli ve evaluator kaynaklarını sabitle.
.\.venv\Scripts\python.exe -m experiments.independent_validation freeze --bundle .checks/frozen-word-char-v1

# İleride gerçek yeni risk verisi geldiğinde:
.\.venv\Scripts\python.exe -m experiments.independent_validation risk --bundle .checks/frozen-word-char-v1 --csv reports/private/new-risk.csv --attestation reports/private/new-risk-source.json --output .checks/new-risk-run

# Farklı, gerçek yeni audit verisi geldiğinde:
.\.venv\Scripts\python.exe -m experiments.independent_validation audit --bundle .checks/frozen-word-char-v1 --csv reports/private/new-audit.csv --attestation reports/private/new-audit-source.json --risk-result .checks/new-risk-run/risk_result.json --output .checks/new-audit-run
```

Paket ve çıktı dizinleri önceden mevcutsa araç üzerine yazmaz. Gerçek risk sonucu
audit'e verilmeden önce receipt hash'i ve risk tahmin dosyaları doğrulanır;
değiştirilmiş eşikler veya dosyalar kabul edilmez. Hash'ler yanlışlıkla değişiklik
tespiti içindir; imzalı/harici bir güven otoritesi yerine geçmez. Yalnız kendi
oluşturduğunuz güvenilir yerel joblib paketlerini kullanın.

Çıktılar `.checks` veya `reports/private` altında kalmalı; ticket metinleri ve
satır bazındaki sonuçlar Git'e eklenmemelidir. Yeni bağımsız veri olmadığı sürece
yalnız freeze işlemi ve sentetik otomasyon testleri çalıştırılır.

## Bu oturumda gerçekten yapılanlar

- `.checks/frozen-word-char-v1` paketi oluşturuldu; yukarıdaki freeze komutu bu
  dizin için yeniden çalıştırılmamalıdır. Mevcut model dosyaları ve kaynak
  snapshot'ı tekrar doğrulandı.
- Aday hash'i `d3c997c2d12d7ea793cf7db6f4dd6bd200a5da428a877fa4e657439f9aae4378`;
  referans hash'i `ea6b1f9ca0075bd32ee39d01a249b4b8860537f576e52ba8e8afc6dd1a169843`.
- Paylaşılabilir manifest ve hazırlık durumu
  [`reports/development/2026-11-12`](../reports/development/2026-11-12/) altında.
  `independent_validation_readiness.json` gerçek değerlendirme sayısını **0**
  olarak kaydeder. Manifest, yeni veride başarı raporu değildir.
- Veri kabul, model/kaynak bütünlüğü, risk/audit ayrımı ve eşik değişmezliği için
  19 sentetik test eklendi. Tam takım **144 geçti**, 94 bağımlılık uyarısı,
  12,64 saniye. Uyarılar mevcut joblib/NumPy ve TestClient bağımlılıklarından;
  daha fazla model yükleme testi uyarı sayısını artırır.
- Ruff ve strict mypy geçti (58 kaynak dosya). Yeni testler CI listesine eklendi;
  hosted CI koşusu başlatılmadı.
- Yeni gerçek veri bulunmadığı için risk veya audit komutları gerçek veriyle
  çalıştırılmadı. Sentetik örnekler testlerin geçici dizinlerinde kaldı.

## Sonraki veri araması ve stres testi

İnternetten insan etiketli gerçek bir corpus indirildi; yedi servis etiketi mevcut sekiz sınıfla uyumlu olmadığı için doğrudan audit girdisi yapılmadı. Ayrıca 80 kurmaca senaryodan 240 ilişkili varyant oluşturulup iki modelde çalıştırıldı. Olumsuz sonuçlar dahil ayrıntılar [dış veri ve stres testi raporunda](EXTERNAL_DATA_AND_STRESS_2026-11-12.md). Uyumlu gerçek sekiz sınıflı bağımsız audit hâlâ tamamlanmış değil.
