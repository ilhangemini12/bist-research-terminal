# Üretim devam noktası — 2026-10-13

## Son doğrulanmış checkpoint — 13 Ekim

Kod e082c0d + CI düzeltmesi 04a6319; veri 876cb33.
Broker 38369307283, Daily 38369307289, Pages 38371095070 SUCCESS.
Dal checkpoint/broker-integrity-verified-20261013; audit docs/AUDIT_2026-10-13.md.
224 Python testi; 8 Node/formül/UI; 42.442 Excel alanı; gerçek Chromium mobil/offline PASS.
Üretim 2026-10-13T08:42:10 UTC, kapanış 12 Ekim. Genel PARTIAL319/323;
AFYON/ISATR/KARCL/OZRDN son koşuda NoData. 100 yeni sermaye kontrolü önceki
100'lük kümeden farklı; HTTP429'da duruldu. Q2 305 değişmeyen kayıt doğrulandı.
Broker loader son portföyü bütün seçer, çıkarılan üyeyi diriltmez, sonraki
zamanda alınmış gözlemi geçmişe taşımaz. Aynı kurum iki kaynak sayılmaz.
10 Gedik hedefi 13 Ekim gözlemli; tek kurum/konsensüs yok. Deniz resmi açık
sayfasında hedef tablosu bulundu; üretim entegrasyonu henüz yapılmadı.
İlk CI giriş noktası import hatası audit'te kayıtlı; düzeltilen koşular başarılı.

## Önceki doğrulanmış checkpoint

Kod c804b33; veri 15864a3. Daily 38316391640 ve Pages 38316489428 SUCCESS.
Sabit dal: checkpoint/handoff-verified-20261012. 211 Python testi; 8 Node testi;
42.442 Excel skaler alan; gerçek Chromium mobil/offline kabulü PASS.
Canlı Run VALUE 51; tarih 2026-10-12, üretim 22:24:28 UTC. Sağlık PARTIAL:
319/323 fiyat/tarihçe; AFYON/KARCL/OZRDN tutarsız OHLC, ISATR kaynak eksikliği.
Son koşu ortak KAP devresi nedeniyle sıfır mali indirme ve sıfır sermaye isteği.
Detaylı kanıt ve PDF/ZIP ayrımı docs/AUDIT_2026-10-12.md içinde.

## Son uygulama turu

12 Ekim audit: docs/AUDIT_2026-10-12.md; kaynak izin incelemesi:
docs/SOURCE_REVIEW_2026-10-12.md. Mobil taslaklar artık çalışma koduna entegre;
Run yayımlanan veriyi tarar, GitHub işini tetiklemez. Kaynak kontrollü PWA ve
Excel/canonical karşılaştırması iş akışı kabul kapılarına eklendi.
KAP mali dönem devresi ile host devresi ayrıldı; eski bilinmeyen hata aşamaları
kanıtsız sınıflandırılmaz. Sermaye kontrolleri en eski gözlemi önceleyen sırada.
Son canlı kabul SHA/run bilgisi audit'ten okunmalı; yalnız yerel test yayın kanıtı değildir.

Testler: python -m pytest; node dashboard/tests/formula.test.js;
node dashboard/tests/ui_regression.test.js;
node --test dashboard/tests/research.test.js tests/pwa.test.js;
python scripts/validate_excel_snapshot.py.
Gerçek tarayıcı: Playwright 1.56.1 + Chromium kur; dashboard'u HTTP üzerinden sun;
BIST_E2E_URL ile node dashboard/tests/browser_e2e.cjs çalıştır. Pages bunu yayın öncesi yapar.
S24 Ultra: terminali Chrome'da aç → Telefona yükle veya ⋮ → Ana ekrana ekle.
Fon sahipliği, yabancı payı/değişimi ve ikinci broker henüz uygulanmış sayılmaz.

Kaynak gerçekliği: canlı main HEAD, Actions sonuçları, dashboard/data/latest.json,
dashboard/data/health.json, artifacts/build_report.json ve data/state/production_checkpoint.json.
Sohbet kotası otomatik GitHub Actions veri yenilemesini durdurmaz; sohbet dışında
kesintisiz kod geliştirme yapılacağı varsayılmaz.

## Güvenli devam

1. Canlı HEAD ve son Daily Update / Deploy Pages / Broker Target Refresh sonuçlarını oku.
2. health ve refresh alanlarını kontrol et: başarılı iş akışı tam veri kapsamı demek değildir.
3. data/state günlük KAP kontrol makbuzlarını ve immutable Parquet parçalarını geri yükle.
   History imleci restore edilen DuckDB verisindeki son gündür; yeniden bootstrap etme.
4. Bir değişiklikten önce checkpoint dalı aç; EDIT → TEST → LIVE VERIFY → CHECKPOINT uygula.
5. python -m pytest; node dashboard/tests/formula.test.js; node dashboard/tests/ui_regression.test.js.
6. Gerçek Daily Update çalıştır. Yeni güncel JSON, Excel ve build report aynı canonical girdiden
   üretilmeli; validate_production.py doğrulama etiketlerini ve teknik tarihlerini kontrol eder.
7. Pages güncel üretim çıktısını yayımladıktan sonra tekrar karşılaştır.

## Zamanlama ve kesinti

Daily Update UTC 17:35 ve 20:35 hafta içi; UTC 07:35 her gün kapanmış seans için toparlama.
GitHub zamanlaması gecikebilir. İstanbul 19:00 öncesi güncel seans kapanmış sayılmaz.
Takvim yılı eşleşmiyorsa yayın durur ve takvim gözden geçirilmelidir.
Başarısız çalışmada yalnızca tamamlanmış kalıcı veri parçaları/makbuzları checkpoint edilir;
başarısız dashboard çıktısı yayımlanmaz. Günlük makbuzlar KAP istek tekrarını sınırlar.

## Bu değişikliğin gerekçesi

9 Ekim eski main 82c0512: fiyat doğrulaması 155/323, history 1 Ekim'de.
ISATR boş Yahoo serisinin SchemaChanged sayılması kalan 167 sembolü global devre kesiciye
sokuyordu. Boş sembol serisi artık NoData; gerçek şema/erişim hataları devreyi açar.
Günlük akış eksik history günlerini tamamlar ve aynı Yahoo gözlemini fiyat doğrulamasında
kullanır (ayrı ikinci kaynak sayılmaz). KAP açık sermaye ve son iki kapanmış çeyrek
arşivi günlük kontrol edilir; yüksek güven şartı düşürülmez.

## Sınırlar / sonraki işler

- VERIFIED_2X için iki bağımsız upstream gerekir. ISATR bağımsız ikinci kanıt yoksa tek kaynak/eksik.
- Eski fiyat/geçmiş veri güncelmiş gibi gösterilmez; eski tekniklerde metrikler N/A olur.
- History günlük ekleme yapar; geçmiş corporate action / adjusted-close revizyonlarını yeniden
  uzlaştırmaz. Backtest için bu sınırlama ve 2026-10-01 öncesi üye geçmişi yanlılığı korunur.
- KAP yeniden kontrolü başarısızsa son iyi bilanço/sermaye korunur, refresh durumu PARTIAL/BLOCKED;
  financial period ve capital_retrieved_at tüketiciye açıktır. Tüm mali değerler günlük yayımlanmaz.
- Tek broker gerçek konsensüs değildir. Eksik KAP eşlemeleri ve ikinci ücretsiz broker ayrı işlerdir.
- ZERO_COST_ONLY, kaynak soy ağacı ve yeniden dağıtım sınırları korunmalı; resmi ham bülten/arşiv
  kamu deposuna konulmamalı.

Canlı doğrulama sonuçları tamamlandığında docs/AUDIT_2026-10-12.md güncellenir.
