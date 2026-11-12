# Dış veri araması ve sentetik stres testi — 12 Kasım 2026

Kapsam notu: bu belge ek geliştirme/kuruma uyarlama araştırmasıdır. Mevcut veri kümesinde tamamlanan benchmark sonucunu değiştirmez ve referans uygulamanın tamamlanması için yeni bir zorunluluk tanımlamaz. [Proje kapsamı ve yol haritası](PROJECT_SCOPE.md).

Kullanıcının talebiyle hem internette gerçek veri arandı hem de ayrıca sentetik
bir stres seti oluşturulup çalıştırıldı. Sonuçlar yeni bir eğitim veya model
terfisi için kullanılmadı. Başarısız senaryolar sonuçlara bakılarak değiştirilmedi.

## Gerçek veri bulundu ve indirildi

Kaynak: Leonardo Santiago Benitez Pereira, **Classification of IT Support
Tickets**, [Zenodo v1](https://zenodo.org/records/7384758),
DOI `10.5281/zenodo.7384758`. Yayıncı, gerçek bir IT şirketinden alınan 2.229
biletin üç IT uzmanı tarafından 2020'de sınıflandırıldığını; anonimleştirme ve
manuel kontrol uygulandığını belirtiyor. Veri çok dilli; English, German,
Portuguese ve Spanish içeriyor. [Yayıncı metadata API'si](https://zenodo.org/api/records/7384758)
lisansı `cc-by-4.0` olarak veriyor. Atıf: Pereira, Leonardo Santiago Benitez,
*Classification of IT Support Tickets*, Zenodo, 2022, CC BY 4.0.

`X_train`, `X_test`, `y_train`, `y_test` CSV'leri indirildi; dört dosyanın MD5'i
hem yayıncı metadata'sıyla hem sabitlenmiş checksum'larla doğrulandı. Model,
tokenizer veya encoder pickle dosyaları indirilmedi/yüklenmedi.
[Yeni v2 kayıt](https://zenodo.org/records/7648117) metadata'sı da kontrol edildi:
dört CSV'nin checksum'ları v1 ile aynı; bunlar iki ayrı yeni veri kümesi değil.

Metin ve etiket dosyaları ID üzerinden bire bir birleştirildi. Etiketler gerçekten
CSV'den okundu; ikincil repo açıklamalarındaki farklı kategori listeleri esas
alınmadı. Veri, QueuePilot'un sekiz sınıfı yerine şu servis gruplarını içeriyor:

| Yayıncının sınıfı | Satır |
| --- | ---: |
| Support general | 762 |
| Fileservice | 684 |
| Software | 222 |
| O365 | 219 |
| Active Directory | 133 |
| Computer-Services | 106 |
| EOL | 103 |

Kendi kontrollerimizde:

- 2.229 satır, 1.471 farklı normalleştirilmiş metin; 758 tekrar satırı.
- Bir normalleştirilmiş metin grubunda birden fazla kaynak etiketi var.
- Kaynağın train/test dosyaları 33 normalleştirilmiş metni paylaşıyor.
- QueuePilot'un eski ham veri metinleriyle normalize edilmiş bire bir örtüşme: 0.
- Etiket şemasına doğrudan uyan kaynak sınıfı: 0.

Örtüşmenin sıfır olması tüm yakın kopyaların bulunmadığını veya aynı hedef
dağılımından bağımsız örneklem elde edildiğini kanıtlamaz. Kaynağın kendi
train/test adları bizim eski veri bölümlerimiz anlamına da gelmez.

**Karar:** gerçek dış veri kaynağı elde edildi, ancak mevcut sekiz sınıflı
audit'e doğrudan uygun değil. `Fileservice -> Storage`, `O365 -> Access` gibi
eşleştirmeler uydurulmadı; bir servis grubu birden fazla problem türünü kapsayabilir.
Bu corpus üzerinde sekiz sınıflı doğruluk hesaplanmadı. Kullanılabilmesi için
gerekçeli taksonomi uyumu veya bağımsız yeniden etiketleme, tekrar gruplarıyla
bölme ve dil/dağılım kapsamının belirlenmesi gerekir.

Ham CSV'ler yalnız `reports/private/external/zenodo-7384758` altında. Paylaşılabilir
kanıt: [public_source_qualification.json](../reports/validation/2026-11-12/public_source_qualification.json).

## Diğer kaynakların sonucu

- [Mendeley IT Incidents](https://data.mendeley.com/datasets/7pfzrjpct7/1),
  Endava/Microsoft destek sınıflandırma deposuna kaynak bağlantısı veriyor.
  [Özgün depo](https://github.com/gabrielpreda/Support-Tickets-Classification)
  operasyonel sınıfların sayısal kodlandığını ve metinlerin işlendiğini açıklıyor.
  Doğrudan sekiz sınıf uyumu doğrulanamadı. Bağlı Azure CSV adresinde DNS hatası
  alındı; içerik indirilmediği için aynı metinlerin bulunduğu iddia edilmedi.
- [Tobi-Bueck corpus kartı](https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets)
  farklı bir queue şeması ve CC BY-NC 4.0 lisansı listeliyor; sentetik veri
  üretimini de tanıtıyor. Bu veri için bağımsız insan etiketli köken doğrulanmadı;
  gerçek bağımsız audit kaynağı olarak seçilmedi. Bu gözlem corpus'un tamamının
  sentetik olduğuna dair kesin bir iddia değildir.

Arama evrensel bir yokluk kanıtı değil; kontrol edilen kaynaklar ve kararları
[source_search_registry.json](../reports/validation/2026-11-12/source_search_registry.json)
dosyasında kayıtlı.

## Oluşturulan sentetik stres seti

Gerçek corpus'tan ayrı olarak 80 özgün, kurmaca senaryo yazıldı: her sınıfa 10
senaryo. Her senaryodan düz metin, e-posta sarmalayıcısı ve tek yazım hatası olmak
üzere üç varyant üretildi. Toplam 240 satır, **80 ilişkili senaryo grubu** var.
Bu 240 bağımsız gerçek gözlem değildir. Metinler AI tarafından yazıldı; gerçek
kullanıcı bileti oldukları iddia edilmedi. Senaryo metinleri CC0-1.0 olarak sunulur.

Senaryo etiketleri açıkça belirtilmiş geleneksel anlamları kullanır: Access
oturum açma, Administrative rights ayrıcalıklı yetki, Hardware fiziksel arıza,
Storage kapasite/kurtarma, Purchase satın alma, HR personel/izin/maaş,
Internal Project planlı proje, Miscellaneous genel servis masası soruları.
Bu anlamların orijinal eğitim taksonomisiyle eşdeğer olduğu kanıtlanmadı.
Bu yüzden ölçümün adı **sentetik senaryo spesifikasyonuyla uyum**.

Plan ve CSV model tahminlerinden önce hash'leriyle kaydedildi. Eski ham veriye
normalize bire bir örtüşme kontrolü yapıldı; örtüşme yok. İki sabit modelin
ikisine de 0,60 sayısal eşik uygulandı; eşik araması ve eğitim yapılmadı. Adayın
0,60 eşiği yeni üretim eşiği olarak kaydedilmedi; aynı sayı iki modelde aynı
kalibrasyon/coverage noktası anlamına gelmeyebilir.

| Stres ölçümü | Referans | Kelime + karakter adayı |
| --- | ---: | ---: |
| Düz 80 senaryoda spesifikasyon uyumu | 45/80 — %56,25 | 45/80 — %56,25 |
| E-posta varyantında uyum | %41,25 | %46,25 |
| Yazım hatası varyantında uyum | %57,50 | %56,25 |
| Tüm ilişkili varyantlarda uyum | %51,67 | %52,92 |
| 0,60 ile kabul edilen varyant | 142/240 | 153/240 |
| Kabul edilenlerde spesifikasyon uyumu | %61,27 | %59,48 |
| Güveni >=0,80 olan uyumsuzluk | 18 | 25 |

Özellikle ayrıcalıklı yetki anlamıyla yazılan 10 düz Administrative rights
senaryosunda iki model de doğru sınıfı bulamadı. Bu, etiket anlamlarının açıklığa
kavuşturulmasının önemini artırıyor; orijinal gerçek veri performansının sıfır
olduğunu kanıtlamıyor. E-posta çerçevesi eklendiğinde uyumun düşmesi de giriş
biçimine karşı dayanıklılık sorunu için somut bir stres bulgusu.

Olumsuz sonuçlar silinmedi, kolay örnekler eklenerek skor yükseltilmedi. Adayın
checkpoint'teki coverage kazancı, bu yeni senaryo spesifikasyonunda genel
üstünlük olarak tekrarlanmadı. Sentetik sonuçlardan yeni Clopper-Pearson
garantileri veya gerçek üretim doğruluğu iddiaları üretilmedi.

Veri, plan, tahminler ve toplulaştırılmış sonuçlar:
[`synthetic-stress-v1`](../reports/validation/2026-11-12/synthetic-stress-v1/).
Çalıştırma: [`benchmarks/README.md`](../benchmarks/README.md).

## Tamamlanan iş ve kalan sınır

Gerçek veri araması/indirme/kaynak doğrulaması ve sentetik veri üretimi/stres
değerlendirmesi tamamlandı. Ancak QueuePilot'un sekiz sınıfı için uygun yeni
gerçek etiketlerle bağımsız risk/audit doğrulaması **tamamlanmadı**. Bu farkı
sentetik veriyi gerçekmiş gibi beyan ederek kapatmadık. Model terfisi yapılmadı.
Mevcut üretim paketi ve önceki ölçümleri korunuyor; stres bulguları onun yeni
veri ve taksonomilere doğrudan taşınabileceği yönünde bir iddiayı desteklemiyor.

## Çalıştırılan kontroller

- Kaynak checksum bozulması, text/label ID sırası, taksonomi uyumsuzluğu,
  kaynak train/test metin tekrarı, sentetik grup yapısı ve plan sonrası veri
  değişikliğini kapsayan altı yeni test geçti.
- Tam takım: **150 test geçti**, 94 bağımlılık uyarısı, 12,72 saniye.
- Ruff ve strict mypy (63 kaynak dosya) başarılı; `git diff --check` geçti.
- Üretim DVC durumu `{}`; lock'taki 42 çıktı kaydının MD5/byte boyutları ve
  Git'teki lock byte'ları değişmedi. Üretim kaynakları, modelleri ve eşikleri aynı.
- Sabit model paketi, sentetik CSV ve senaryo kaynakları hash kontrollerinden
  geçti. Yeni bir hosted CI koşusu, commit/push veya model terfisi yapılmadı.

Sayısal doğrulama kaydı:
[`verification.json`](../reports/validation/2026-11-12/verification.json).
