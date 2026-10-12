# Kaynak incelemesi — 12 Ekim 2026

Bu belge erişilebilirlik ile saklama/yeniden yayımlama iznini ayırır. Yeni fon,
sahiplik veya ikinci broker sayısal kolektörü bu çalışmada açılmadı.

| Veri ürünü | Resmi kaynak | Doğrulanan durum | Üretim kararı |
|---|---|---|---|
| BES fon getirisi | https://emeklilik.egm.org.tr/eyf-anasayfa | EGM sitesinin güncel yönlendirmesi | NOT_CONFIGURED; izin belgesi yok |
| BEFAS fon listesi | https://www.egm.org.tr/befas/fon-listesi | Erişilebiliyor, alınan sayfa menü kabuğu; fon satırları doğrulanmadı | NOT_CONFIGURED |
| Yabancı sahiplik | https://www.vap.org.tr/ | Saklama/yeniden dağıtım izni doğrulanmadı | BLOCKED_LICENSE_REVIEW; N/A |
| Fonların hisse portföyleri | https://kap.org.tr/ | Fon bildirimi ve raporları aday kaynak; yeni aktarım izni doğrulanmadı | NOT_CONFIGURED; N/A |
| İkinci broker | Henüz doğrulanmış kaynak yok | Mevcut Gedik kayıtları tek broker | Konsensüs yok |

## İncelenen koşullar

- VAP resmi PDF: https://www.vap.org.tr/sites/default/files/2026-09/telif-hakki-ve-cekince-ihbari.pdf
  12 Ekim HTTP indirme ve PDF metin çıkarma ile okundu. Önceden yazılı MKK izni
  olmadan kopyalama, dağıtım ve ileride kullanım için saklama kısıtları var.
- EGM: https://www.egm.org.tr/yasal-uyari/ — 12 Ekim resmi sayfa okundu.
  Ön izin ve kaynak gösterme şartları var. Açık erişim, açık yeniden kullanım
  lisansı sayılmadı.
- KAP: https://kap.org.tr/tr/icerik/Diger/telif-hakki-ve-cekince-ihbari
  — 12 Ekim resmi metin okundu. Bilgi edinme kullanımını açıklıyor; yazılı izin
  olmadan çoğaltma, dağıtma ve saklama kısıtları içeriyor. Mevcut kaynak katalog
  etiketi izin belgesi değildir. Mevcut kişisel araştırma/normalize olgu kullanımının
  kamuya dağıtım kapsamı ayrıca incelenmeli; yeni fon raporu aktarımı açılmadı.

Ham rapor/bültenlerin kamuya kopyalanmasına izin çıkarımı yapılmadı. TEFAS erişim
engeli aşılmadı, ücretli servis eklenmedi. Fon getirisi ile fonun bir şirketteki
pay oranı aynı metrik değildir; piyasa toplamı da hisse bazlı yabancı oranı değildir.

## Sonraki somut adım

Saklama ve yeniden kullanım hakkı açık bir kaynak veya hak sahibinden yazılı izin
sağlandıktan sonra önce tek fon/iki tarih pilotu uygulanmalı. ISIN eşlemesi,
rapor/yayın tarihi, pay adedi, şirket toplam payı, hisse bazlı pay ve yüzde-puan
değişimi ayrı alanlar olmalı. Kaynak verisi yoksa N/A kalmalı; VERIFIED_2X etiketi
bağımsız iki upstream kanıtı olmadan verilmemeli.
