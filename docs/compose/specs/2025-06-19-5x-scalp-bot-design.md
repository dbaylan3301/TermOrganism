# 5x Scalp Bot — Design Spec

## [S1] Problem
Kripto futures işlemlerinde otomatik sinyal üretimi ve pozisyon takibi için terminal tabanlı bir araç gerekli. Kullanıcı manuel olarak işlem yapar, bot sinyal üretir ve pozisyonu canlı takip eder.

## [S2] Çözüm
TermOrganism'e entegre edilecek `plugins/scalpbot/` modülü:
- Çoklu USDT perpetual çiftini otomatik tarar
- EMA crossover, RSI, ATR, hacim spike koşullarını değerlendirir
- Uygun koşulda sinyal üretir ve detaylı çıktı verir
- Kullanıcı pozisyon aldığında fiyatı canlı takip eder
- En iyi çıkış noktasını önerir

## [S3] Sinyal Koşulları

### Veri
- 1 dakikalık kline, son 200 bar
- Kapsanan çiftler: Binance USDT perpetual listesi (volume sıralaması ile top 50)

### İndikatörler
| İndikatör | Parametre | Kullanım |
|-----------|-----------|----------|
| EMA | 8, 13 | Crossover tespiti |
| RSI | 14 | Aşırı alım/satım filtresi |
| ATR | 7 | Volatilite eşiği + SL/TP hesaplama |
| Hacim | 5 bar / 14 bar ort. | Spike tespiti |

### LONG Koşulları (Tümü sağlanmalı)
1. EMA8, EMA13'ü yukarı keser (son 2 barada crossover)
2. RSI14 < 62
3. ATR% > %0.18 (son bar)
4. Son 5 bar hacmi > son 14 bar ortalaması × 1.9
5. Fiyat, son kapanışın +12 bps üzerinde

### SHORT Koşulları (Tümü sağlanmalı)
1. EMA8, EMA13'ü aşağı keser (son 2 barada crossover)
2. RSI14 > 38
3. ATR% > %0.18 (son bar)
4. Son 5 bar hacmi > son 14 bar ortalaması × 1.9
5. Fiyat, son kapanışın -12 bps altında

### Risk Parametreleri
| Parametre | Değer |
|-----------|-------|
| Kaldıraç | Sabit 5x |
| SL | ATR(7) × 1.5 |
| TP | ATR(7) × 1.7 |
| Hedef | Günde 3-5 sinyal |

## [S4] Çalışma Akışı

```
┌─────────────────────────────────────────┐
│  SCANNER: Coin listesini döngüde tara   │
│  (her coin için 1dk kline çek)         │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  SIGNAL: İndikatörleri hesapla          │
│  Koşulları kontrol et (AND mantığı)    │
└──────────────────┬──────────────────────┘
                   │
          Sinyal var mı?
          ┌────┴────┐
          │ EVET    │ HAYIR
          ▼         ▼
┌──────────────┐  ┌──────────────┐
│ Sinyal Çıktı │  │ Bekle →      │
│ + Detaylar   │  │ Sonraki bar  │
└──────┬───────┘  └──────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Kullanıcı "pozisyon_al" der           │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  TRACKER: Canlı fiyat izleme (1sn)     │
│  P&L hesabı, SL/TP seviyeleri          │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  EXIT: RSI/ATR/trailing ile çıkış      │
│  Sonuç raporu + kümülatif performans    │
└─────────────────────────────────────────┘
```

## [S5] Çıktı Formatları

### Sinyal Çıktısı
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 SHORT SİNYAL — BTCUSDT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 2025-06-19 14:32 UTC
Giriş Fiyatı:  $67,450.20
SL:            $68,120.50 (−0.99%)
TP:            $66,890.10 (+0.83%)
Kaldıraç:      5x
Risk/Kazanç:   1:1.13
Potansiyel K/Z: +4.17% (TP) / −4.97% (SL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Koşullar:
  ✓ EMA Crossover (EMA8: 67,520 > EMA13: 67,480)
  ✓ RSI: 42.3 (> 38)
  ✓ ATR%: 0.24% (> 0.18%)
  ✓ Vol Spike: 2.1x (> 1.9x)
  ✓ Trigger: −15 bps (< −12 bps)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Komut: pozisyon_al BTCUSDT SHORT $67,450.20
```

### Pozisyon Takip Çıktısı
```
┌─────────────────────────────────────────┐
│ 📊 POZİSYON AÇIK — BTCUSDT SHORT 5x   │
├─────────────────────────────────────────┤
│ Giriş:      $67,450.20                 │
│ Güncel:     $67,120.50                 │
│ P&L:        +$162.50 (+2.41%)          │
│ SL:         $68,120.50 (−0.99%)       │
│ TP:         $66,890.10 (+0.83%)       │
│ Süre:       12 dk 34 sn               │
│ Kalan:      TP'ye $230.40 / SL'e $670  │
├─────────────────────────────────────────┤
│ Grafik: ▁▂▃▄▅▆▇█▇▆▅ (son 20 dk)      │
└─────────────────────────────────────────┘
```

## [S6] Modül Yapısı

```
plugins/scalpbot/
├── __init__.py          # Modül init, komut kaydı
├── scanner.py           # Coin listesi yönetimi, döngü
├── indicators.py        # EMA, RSI, ATR, Volume hesapları
├── signals.py           # Sinyal koşulları evaluasyonu
├── tracker.py           # Pozisyon takibi, canlı fiyat
├── risk.py              # SL/TP/exit mantığı
├── display.py           # Terminal formatları, paneller
└── config.py            # Parametreler (EMA periyotları, vb.)
```

## [S7] Hata Yönetimi
- Binance API bağlantı hatası → 5sn bekle, yeniden dene
- Geçersiz veri → atla, log kaydet
- Tüm pair'ler başarısızsa → 30sn bekle, listeyi yenile
- Pozisyon takibinde bağlantı koparsa → son bilinen fiyattan devam et

## [S8] Test Stratejisi
- Unit test: indicators.py, signals.py (mock veri ile)
- Integration test: scanner → signals akışı
- Manual test: Gerçek Binance verisi ile canlı tarama
