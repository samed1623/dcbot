# Gray Zone Warfare Discord Bot

Bu Discord botu Gray Zone Warfare oyunu için wiki bilgileri sağlar ve kullanıcılarla sohbet edebilir.

## Özellikler

### 📚 Wiki Özellikleri
- Gray Zone Warfare silahları, görevleri ve haritaları hakkında detaylı bilgiler
- İnteraktif kategori ve öğe seçimi
- Gelişmiş arama fonksiyonu
- Geçici kanallar ile özel wiki deneyimi

### 💬 Sohbet Özellikleri (Yeni!)
- Doğal Türkçe sohbet desteği
- Akıllı pattern matching ile anlamlı yanıtlar
- Rastgele bilgi paylaşımı
- Selamlaşma, soru-cevap ve günlük konuşmalar

## Komutlar

### Wiki Komutları
- `!wiki` - Ana wiki menüsünü açar
- `!wiki ara <kelime>` - Wiki'de arama yapar

### Sohbet Komutları
- `!yap <mesaj>` - Botla sohbet edersiniz
- `!random` - Rastgele bir bilgi paylaşır
- `!komutlar` - Bot komutlarını listeler

### Yönetici Komutları
- `!setlogchannel` - Log kanalını ayarlar

## Kurulum

1. Gerekli Python paketlerini yükleyin:
```bash
pip install discord.py python-dotenv
```

2. `.env` dosyasında Discord bot token'ınızı ayarlayın:
```
DISCORD_TOKEN=your_bot_token_here
```

3. Botu çalıştırın:
```bash
python bot.py
```

## Dosya Yapısı

- `bot.py` - Ana bot kodu
- `wiki.json` - Gray Zone Warfare wiki verileri
- `chat_data.json` - Sohbet yanıtları ve desenleri
- `config.json` - Bot konfigürasyonu
- `.env` - Discord token (gizli)

## Özellikler

- **Türkçe Desteği**: Bot tamamen Türkçe arayüz kullanır
- **Geçici Kanallar**: Wiki etkileşimleri için otomatik kanal oluşturma
- **Akıllı Sohbet**: Pattern matching ile doğal konuşma
- **Gelişmiş Loglama**: Discord kanalında aktivite logları
- **Otomatik Kurulum**: Yeni sunucularda otomatik setup

## Sohbet Özellikleri

Bot şu tür mesajlara yanıt verebilir:
- Selamlaşmalar (merhaba, selam, günaydın)
- Nasılsın soruları
- Teşekkürler
- Günlük konuşmalar (kahve, müzik, hava durumu)
- Oyun konuları
- Yardım talepleri
- Ve çok daha fazlası!

## Geliştirme

Bu bot, minimal değişikliklerle mevcut wiki fonksiyonalitesine sohbet özelliği eklemek için tasarlanmıştır. Yeni sohbet sistemi:

- Mevcut wiki sistemini etkilemez
- Basit pattern matching kullanır
- Kolayca genişletilebilir
- Türkçe dil desteği ile optimize edilmiştir