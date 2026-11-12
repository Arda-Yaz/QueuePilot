# Taksonomi araştırması ve kör etiketleme pilotu — 12 Kasım 2026

Kapsam notu: bu belge ek geliştirme/kuruma uyarlama araştırmasıdır. Mevcut veri kümesinde tamamlanan benchmark sonucunu değiştirmez ve referans uygulamanın tamamlanması için yeni bir zorunluluk tanımlamaz. [Proje kapsamı ve yol haritası](PROJECT_SCOPE.md).

## Kaynaktan doğrulanan ve doğrulanamayan bilgi

[Orijinal Kaggle sayfası](https://www.kaggle.com/datasets/adisongoh/it-service-ticket-classification-dataset)
ve [yayıncı metadata API'si](https://www.kaggle.com/api/v1/datasets/view/adisongoh/it-service-ticket-classification-dataset)
kontrol edildi. API yanıtı yerelde korunup hash'lendi. Sürüm 1, iki alan
(`Document`, `Topic_group`), 47.837 satır ve sekiz sınıf adı doğrulanabiliyor.
Metadata lisansı CC0: Public Domain olarak belirtiyor.

İncelenen yayıncı metadata'sı sınıfların dahil etme/dışlama koşullarını,
etiketleyici talimatlarını veya etiketleme sürecini açıklamıyor. Yerel notebook
ve kaynak kayıtlarında da bu anlamları otoritatif biçimde tamamlayan bir rehber
bulunmadı. Bu nedenle **orijinal sınıf anlamları doğrulanmış sayılmadı**.
Bu sonuç, başka yerde hiçbir rehber bulunmadığına dair evrensel bir iddia değil.

Sayısal kayıt:
[`taxonomy_source_evidence.json`](../reports/annotation/2026-11-12/taxonomy_source_evidence.json).

## Train verisinin gösterdiği örüntüler

Model tahminleri kullanılmadan yalnız train metin/etiketleri üzerinde kelime
örüntüsü çıkarıldı. Sınıf ortalama TF-IDF ve genel ortalamaya göre ayrıştırıcılık
kullanıldı; en az 10 sınıf belgesinde görülen ifadeler tutuldu. Bunlar sınıf
tanımları değil, **mevcut etiketlerle ampirik ilişkilerdir**.

| Eski etiket | Öne çıkan train ifadeleri | Çözülemeyen sınır |
| --- | --- | --- |
| Access | confluence, card, license, password, user | Hesap erişimi, lisans ve uygulama yetkileri aynı grupta görünebiliyor |
| Administrative rights | upgrade, outlook, windows, windows upgrade, issues | Yönetici yetkisi mi, uç cihaz yazılım/OS desteği mi? |
| HR Support | starter, form, new starter, error, leave | Personel süreci ile hesap açma talepleri nasıl ayrılıyor? |
| Hardware | monitor, laptop, meeting, room, cable | Fiziksel arıza ile oda/bağlantı hizmeti kapsamı |
| Internal Project | code, project, codes, setup, pipeline | Proje kodu/kurulum hizmeti ile planlı proje koordinasyonu |
| Miscellaneous | change, add, approval, owner, approve | Grup/listeler/onay akışları ile genel servis soruları |
| Purchase | po, purchase, purchase po, purchased, item | Satın alma ile lisans aktivasyonu/erişimi |
| Storage | wants, mailbox, folder, accept decline, decline | Depolama kapasitesi ile klasör/posta kutusu erişim yetkileri |

Bu kanıt özellikle önceki sentetik stres testinin yorumunu daraltır: o testte
Administrative rights geleneksel ayrıcalıklı yetki anlamıyla, Storage ise kapasite
ve kurtarma anlamıyla tanımlanmıştı. Eğitim etiketleri farklı bir operasyonel
sınıflamayı yansıtıyor olabilir. Stres puanları silinmedi; fakat bu puanlar eski
taksonomiye göre gerçek model doğruluğu veya tek başına model hatası kanıtı değildir.

Örüntüleri kaynak otoritesinin yerine koyarak etiketler yeniden adlandırılmadı.
Örneğin Administrative rights doğrudan Software diye değiştirilmedi, bütün
paylaşım istekleri de otomatik Storage yapılmadı.

## İnceleme için açık öneri rehberi

[`annotation/taxonomy_v1.json`](../annotation/taxonomy_v1.json) sınıf başına dahil
etme/dışlama kurallarını tanımlar. Durumu `proposal_requires_domain_adjudication`;
`equivalent_to_original_training_taxonomy=false`. Bu, eski veri setinin
doğrulanmış sözlüğü veya aktif modelin yeni etiketi değildir.

Temel öneri ayrımları:

- Olağan kimlik doğrulama ve kullanıcı kaynağı izinleri: Access.
- Açık admin/root/sudo/elevated yetki talepleri: Administrative rights.
- Açık fiziksel cihaz arızası: Hardware; her yazdırma hatası donanım sayılmaz.
- Kapasite, yedek/kurtarma ve dosya kalıcılığı: Storage; erişim izni otomatik Storage sayılmaz.
- Ticari alım/sipariş/teklif: Purchase; yalnız kurulum veya aktivasyon satın alma değildir.
- Personel/izin/maaş iş süreci: HR Support; stajyere hesap açma sırf stajyer sözcüğü nedeniyle HR değildir.
- Açık planlı proje koordinasyonu: Internal Project; metindeki project sözcüğü yeterli değildir.
- Genel servis masası süreç bilgisi: Miscellaneous; bilinmeyen her talep buraya atılmaz.

Bu katı öneri genel yazılım, ağ, mesajlaşma ve güvenlik hizmetlerinin tümünü
kapsamıyor. Bunlar eski sekiz sınıfa zorla dağıtılmak yerine `OUT_OF_SCOPE` veya
`TAXONOMY_REVIEW` olarak kaydedilir. Eksik bağlam `INSUFFICIENT_CONTEXT`, baskın
isteği olmayan farklı talepler `MULTI_INTENT` olarak ayrılır.

## Gerçek veride 64 kayıtlık kör pilot

Kaynak: Pereira'nın [Zenodo corpus'u](https://zenodo.org/records/7384758), CC BY 4.0.
Kaynak metin/etiket CSV checksum'ları doğrulandı. Normalleştirilmiş metinler grup
halinde tekilleştirildi; çelişkili kaynak etiketi olan bir grup karantinaya alındı.
Eski ham veriyle bire bir normalize metin örtüşmesi yok.

1.470 uygun farklı metin grubu kaldı. Sabit seed42 hash sırasıyla 64 grup seçildi;
model skoru, kaynak servis kategorisi veya kolay örnek seçimi kullanılmadı.
1.406 grup ayrı `reserved_unreviewed_pool.csv` listesine kondu. Liste bir audit
seti değil; henüz incelenmemiş havuzdur ve gelecekte kullanılabilirliği ayrıca
doğrulanmalıdır.

Etiketleme sırasında görülen dosyada yalnız metin, yerel pilot ID ve metin hash'i
vardı; kaynak servis etiketi ve model tahmini yoktu. Kaynak lineage ayrı dosyada
tutuldu. 64 metin için tam metne dayanan gerekçe ve geçici AI kararı kaydedildi.

| Geçici pilot kararı | Kayıt |
| --- | ---: |
| Öneri rehberiyle sınıf atanabilir | 23 |
| Yetersiz bağlam | 20 |
| Önerilen sekiz sınıfın kapsamı dışında | 13 |
| Taksonomi sınırı kararı gerekli | 7 |
| Çoklu istek | 1 |

Atanabilir 23 kaydın geçici dağılımı Access 20, Administrative rights 2 ve Storage
1. Bu dağılım, dış corpus'un gerçek hedef dağılımına veya sekiz sınıfın tümüne
dair iddia değildir. Özellikle yazılım/ağ/mesajlaşma taleplerinin önerideki
kapsam boşluğunu ve kısa başlıkların bilgi eksikliğini görünür kılar.

**İnsan onaylı kayıt: 0. Gold kayıt: 0.** AI güven alanı kalibre edilmiş olasılık
değil, inceleme notudur. Bu öneriler bağımsız uzman etiketlemesinin yerine geçmez.
İncelenen pilot geliştirme verisidir; sonradan insan onayı almak onu yeni bağımsız
audit verisine dönüştürmez. Araç bu tür audit kullanımını reddeder.

## İnsan incelemesi için hazır dosyalar

Tam metinler ve inceleme dosyaları Git'in yok saydığı
`reports/private/taxonomy-pilot-v1` altında:

- `review_blind.csv`: kaynak kategori ve tahmin olmadan boş inceleme formu.
- `provisional_annotations.csv`: AI önerisi, gerekçe ve boş insan kararı alanları.
- `ai_proposals.json`: satır ID'siyle tam gerekçeli öneri kaydı.
- `hidden_source_lineage.csv`: yalnız adjudication aşamasında açılacak kaynak etiketleri.
- `pilot_group_members.csv`: aynı metne bağlı tüm kaynak ID'leri.
- `reserved_unreviewed_pool.csv`: pilotla kesişmeyen, henüz incelenmemiş gruplar.
- `quarantined_conflicts.csv`: kaynak etiket çelişkileri.

Kaynak anonimleştirme beyanına rağmen metinlerde kalıntı tanımlayıcılar bulunabilir;
tam metinler yayımlanmadı. Paylaşılan raporlar yalnız sayılar, durumlar, genel
kelime örüntüleri ve hash'lerdir. Atıf: Leonardo Santiago Benitez Pereira,
*Classification of IT Support Tickets*, Zenodo, 2022, DOI 10.5281/zenodo.7384758,
CC BY 4.0.

## Karara bağlanması gereken somut sınırlar

1. Eski etiketleri bire bir korumak isteniyorsa, eski kaynağın kuralları veya
   yetkili alan sahibinin açıklaması gerekir. Train kelimelerinden kesin sözlük çıkarılamaz.
2. İş anlamına göre yeni rehber kabul edilecekse bu yeni bir taksonomi sürümüdür;
   eski etiketli train verisi kendiliğinden doğru etiketli hale gelmez. Yeni
   etiketleme ve uygun veriyle yeniden eğitim gerekir.
3. Yazılım/ağ/mesajlaşma/güvenlik desteği bu ürünün kapsamındaysa açık sınıflar
   veya gerekçeli sınırlar tanımlanmalı; Miscellaneous sessizce genişletilmemeli.
4. Paylaşılan posta kutusu oluşturma, posta adresi/listesi bakımı ve dosya kilidi
   örnekleri rehber sınırı kararı gerektiriyor. Belirsizlikler cevaplanmadan bu
   kayıtlar gold veri olarak dışarı verilmemeli.
5. Gerçek bağımsız risk/audit için taksonomi ve örnekleme protokolü sabitlendikten
   sonra, pilot dışında kalan uygun gruplar uzmanlarca tahminlere bakmadan
   etiketlenmeli; dil, tekrar ve temsil kapsamı kontrol edilmeli.

Üretim etiketlerine yeni anlamlar atayan bir değişiklik veya model terfisi
yapılmadı. Bu adımın çıktısı, doğrulanamayan kısmı gizlemeyen kaynak araştırması,
açık bir rehber önerisi ve gerçek metinler üzerinde tamamlanmış geçici pilot
incelemesidir.

## Çalıştırılan doğrulamalar

- Kör örnekleme, ID bütünlüğü, zorla etiket atamayı reddetme, değiştirilmiş
  inceleme dosyasını yakalama ve pilotun audit'e dönüşmemesi için 8 test geçti.
- Tam takım: **158 test geçti**, 94 bağımlılık uyarısı, 18,02 saniye.
- Ruff, strict mypy (67 kaynak dosya) ve `git diff --check` başarılı.
- Pilot metin/öneri/taksonomi hash'leri doğrulandı. Ayrılmış 1.406 metin grubu
  pilotun hiçbir tekrar üyesiyle kesişmiyor; insan onaylı yeni gold sayısı sıfır.
- DVC durumu `{}`; 42 üretim çıktı kaydı, üretim kaynakları, model/eşik dosyaları
  ve lock değişmedi. Sabit aday paketi de bütünlük kontrolünü geçti.
- Yeni model eğitimi/terfisi, hosted CI koşusu veya commit/push yapılmadı.

Sayısal kayıt: [`verification.json`](../reports/annotation/2026-11-12/verification.json).
