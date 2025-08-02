import requests
import time
import datetime
import threading
from config import (
    TELEGRAM_TOKEN,
    CHAT_ID,
    PERCENT_UP_THRESHOLD,
    PERCENT_DOWN_THRESHOLD,
    WHALE_VOLUME_USDT,
    CHECK_INTERVAL_SECONDS,
    PRICE_WINDOW_MINUTES,
    BINANCE_API_URL,
)
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Telegram'a mesaj gönder
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram gönderim hatası:", e)

# Binance Futures sembollerini çek
def get_futures_symbols():
    try:
        url = f"{BINANCE_API_URL}/fapi/v1/exchangeInfo"
        response = requests.get(url)
        data = response.json()
        return [
            s["symbol"]
            for s in data["symbols"]
            if s["contractType"] == "PERPETUAL" and s["symbol"].endswith("USDT")
        ]
    except Exception as e:
        print("Coin listesi alınamadı:", e)
        return []

# Son fiyat ve 24 saatlik hacmi al
def get_price_and_volume(symbol):
    try:
        url = f"{BINANCE_API_URL}/fapi/v1/ticker/24hr?symbol={symbol}"
        response = requests.get(url)
        data = response.json()
        return float(data["lastPrice"]), float(data["volume"])
    except Exception as e:
        print(f"{symbol} veri alınamadı:", e)
        return None, None

# Ana takip fonksiyonu
def price_monitor():
    symbols = get_futures_symbols()
    prices = {}
    volumes = {}
    interval_sec = CHECK_INTERVAL_SECONDS

    print(f"{len(symbols)} coin takip ediliyor...")

    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        print(f"[{now.strftime('%H:%M:%S')}] Veriler kontrol ediliyor...")

        for symbol in symbols:
            price, volume = get_price_and_volume(symbol)
            if price is None or volume is None:
                continue

            if symbol not in prices:
                prices[symbol] = price
                volumes[symbol] = volume
                continue

            price_change_percent = ((price - prices[symbol]) / prices[symbol]) * 100
            volume_diff = volume - volumes[symbol]

            if price_change_percent >= PERCENT_UP_THRESHOLD:
                message = (
                    f"📈 {symbol} son {PRICE_WINDOW_MINUTES} dakikada % {price_change_percent:.2f} YÜKSELDİ\n"
                    f"Fiyat: {price}\nHacim artışı: {volume_diff:.2f}"
                )
                send_telegram_message(message)
            elif price_change_percent <= PERCENT_DOWN_THRESHOLD:
                message = (
                    f"📉 {symbol} son {PRICE_WINDOW_MINUTES} dakikada % {abs(price_change_percent):.2f} DÜŞTÜ\n"
                    f"Fiyat: {price}\nHacim değişimi: {volume_diff:.2f}"
                )
                send_telegram_message(message)
            elif volume_diff > WHALE_VOLUME_USDT:
                message = (
                    f"🐋 {symbol} için {volume_diff:.2f} USDT hacim artışı tespit edildi.\n"
                    f"Balina hareketi olabilir."
                )
                send_telegram_message(message)

            prices[symbol] = price
            volumes[symbol] = volume

        time.sleep(interval_sec)

# /durum komutu
async def durum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot çalışıyor ve piyasayı takip ediyor.")

# Telegram botunu başlat
def start_telegram_bot():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("durum", durum))
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=price_monitor, daemon=True).start()
    start_telegram_bot()
