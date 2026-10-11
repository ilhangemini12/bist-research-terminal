# Üretim devam noktası — 2026-10-11

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

Canlı doğrulama sonuçları tamamlandığında docs/AUDIT_2026-10-11.md güncellenir.
