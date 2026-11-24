# Offline akış doğrulaması

24 Kasım 2026’da Windows, Python 3.12.10 ve CPU üzerinde çalıştırıldı. Draft sağlayıcısı `fake` (`extractive-v1`), prompt sürümü `support-draft-v1`. Dense koşusunda gerçek, önceden indirilmiş embedding modeli kullanıldı. İndeksleme ve değerlendirme `HF_HUB_OFFLINE=1` altında tamamlandı. Embedding ortamında sentence-transformers 5.2.0, transformers 4.57.3 ve PyTorch 2.13.0+cpu kullanıldı.

- Corpus `23e3062e0e63a6fcbf8372fdb5825c00653616b6ede595dde690296fdb134f74`, 8 sentetik doküman ve 10 pasaj.
- Dev örnekleri `ac83339a853542c24d6706f44ca5526e7998c6968b3322592002668ef58f4a97`. Final örnekleri `a25c91a08574f2beb0f3d63930217fb586a98c37a466e1040d4beac9d6a5bf15`.
- Chunking `heading-paragraph-v1`, BM25 `k1=1.2, b=0.75`, dense model revizyonu `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`. İki yöntem de aynı final indeks dosyası, pasajlar, sorular, `k=1,3`, 3.500 karakter bağlam bütçesi ve iki ortak terim kapısıyla çalıştı.

```powershell
python -m app.resolution.index index --output .checks/support-index.json
python -m scripts.evaluate_resolution --index .checks/support-index.json --split dev --output .checks/support-dev.json
python -m app.resolution.index download-model
$env:HF_HUB_OFFLINE = "1"
python -m app.resolution.index index --dense --output .checks/support-index-dense.json
python -m scripts.evaluate_resolution --index .checks/support-index-dense.json --split final --retrievers lexical dense --output .checks/support-comparison-final.json
```

| Bölüm ve yöntem | Toplam / cevaplanabilir | Recall@1 | Recall@3 | Cevaplanamaz → inceleme | Retrieval p50 / p95 (ms) | Toplam p50 / p95 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Dev BM25 | 5 / 3 | 3/3 | 3/3 | 2/2 | 0,230 / 0,398 | 17,112 / 20,577 |
| Final BM25 | 6 / 4 | 3/4 | 4/4 | 1/2 | 0,261 / 0,390 | 15,904 / 20,110 |
| Final dense | 6 / 4 | 4/4 | 4/4 | 1/2 | 13,068 / 14,926 | 30,124 / 32,728 |

Recall, kanıt kapısından önceki sıralamada yalnızca cevaplanabilir soruları kapsar. Her örneğin doğru pasaj oranı, örnekler arasında eşit ağırlıkla ortalanır. Süreler her satırdaki tüm örnekleri kapsar. Retrieval ölçümü servis içindeki aday sıralama ve bağlam seçimini içerir. Toplam ölçüm SQLite dahil servis çağrısını kapsar. Model yükleme, evaluator’ın önce çalıştırdığı Recall sıralaması ve HTTP taşıması sürelerin dışındadır. Bu örneklemde p95 gözlenen en yüksek süredir.

## Örneklerin içerik kontrolü

| Örnek | Gözlem |
| --- | --- |
| Dev VPN, yazdırma, takvim | Üç taslak da beklenen adımları içerdi. Her biri bu adımları içeren doğru pasajı gösterdi. |
| Final ortak dosya, Wi-Fi, mikrofon | İki yöntemde de üç taslak beklenen adımları içerdi ve doğru pasajla desteklendi. |
| `final-en-display` | BM25 ilk sıraya VPN profilini koydu, monitör pasajı ilk üçteydi. Dense doğru monitör pasajını ilk sıraya koydu. İki yöntemde de `second screen`, `notebook` ve `hub` gibi ifadeler ortak terim kapısını geçmeye yetmedi. Operatöre `insufficient_evidence` döndü. |
| `final-en-procurement` | İki yöntemde de ortak `headset microphone` terimleri kanıt kapısını geçti. Mikrofon testi taslağı atıf yapılan pasajın içeriğini doğru aktardı. Pasaj, kullanıcının yeni ekipman siparişi isteğine yanıt vermiyordu. Bu, atıf kimliği doğrulanmış bir hatalı taslak örneğidir. |
| `final-tr-travel` | İki yöntemde de taslak boş kaldı ve `insufficient_evidence` döndü. |

Bu sonuçlar küçük sentetik sette retrieval davranışını, çıktı sözleşmesini ve offline akışı ölçer. Fake sağlayıcı pasajı aktarır. Gerçek LLM’in yanıt doğruluğu, anlamsal kaynak desteği, gecikmesi ve maliyeti ölçülmedi. Fake sağlayıcı token kullanımı bildirmedi. Gerçek sağlayıcının istek biçimi ve kullanım alanları HTTP mock ile doğrulandı. [Gerçek sağlayıcı koşusu için yapılandırma ve komut](../README.md#yapılandırma)
