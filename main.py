import os
import time
import requests

# ========== CONFIG ==========

WALLET = "0x1f250Df59A777d61Cb8bd043c12970F3AFE4F925"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

INFO_URL = "https://api.hyperliquid.xyz/info"

CHECK_INTERVAL = 10
RUN_SECONDS = 260

previous_positions = None


# ========== TELEGRAM ==========

def send_message(message):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("Telegram secrets missing")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": CHANNEL_ID,
                "text": message
            },
            timeout=15
        )
        response.raise_for_status()
        print("Telegram message sent")

    except Exception as e:
        print("Telegram error:", e)


# ========== HYPERLIQUID ==========

def get_positions():

    response = requests.post(
        INFO_URL,
        json={
            "type": "clearinghouseState",
            "user": WALLET
        },
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    positions = {}

    for item in data.get("assetPositions", []):

        p = item["position"]

        coin = p["coin"]
        size = float(p["szi"])

        if size == 0:
            continue

        entry = float(p.get("entryPx") or 0)
        pnl = float(p.get("unrealizedPnl") or 0)

        positions[coin] = {
            "size": size,
            "entry": entry,
            "pnl": pnl
        }

    return positions


# ========== POSITION MONITOR ==========

def notify_changes(old, new):

    coins = set(old.keys()) | set(new.keys())

    for coin in coins:

        before = old.get(coin)
        after = new.get(coin)

        # OPEN POSITION
        if before is None and after is not None:

            side = "🟢 LONG" if after["size"] > 0 else "🔴 SHORT"

            send_message(
                "🐋 HYPERLIQUID WALLET TRACKER\n"
                "━━━━━━━━━━━━━━\n"
                "🆕 پوزیشن جدید باز شد\n"
                f"💎 ارز: {coin}\n"
                f"📊 جهت: {side}\n"
                f"📦 حجم: {abs(after['size'])}\n"
                f"💰 قیمت ورود: {after['entry']}\n"
                "━━━━━━━━━━━━━━"
            )

        # CLOSE POSITION
        elif before is not None and after is None:

            send_message(
                "🐋 HYPERLIQUID WALLET TRACKER\n"
                "━━━━━━━━━━━━━━\n"
                "❌ پوزیشن کاملاً بسته شد\n"
                f"💎 ارز: {coin}\n"
                f"📦 حجم قبلی: {abs(before['size'])}\n"
                f"📊 جهت قبلی: "
                f"{'LONG' if before['size'] > 0 else 'SHORT'}\n"
                "━━━━━━━━━━━━━━"
            )

        # POSITION CHANGED
        elif before is not None and after is not None:

            old_size = before["size"]
            new_size = after["size"]

            if old_size * new_size < 0:

                send_message(
                    "🐋 HYPERLIQUID WALLET TRACKER\n"
                    f"🔄 تغییر جهت پوزیشن: {coin}\n"
                    f"جهت جدید: "
                    f"{'🟢 LONG' if new_size > 0 else '🔴 SHORT'}\n"
                    f"حجم جدید: {abs(new_size)}"
                )

            elif abs(new_size) > abs(old_size):

                send_message(
                    "🐋 HYPERLIQUID WALLET TRACKER\n"
                    f"📈 افزایش حجم پوزیشن: {coin}\n"
                    f"حجم قبلی: {abs(old_size)}\n"
                    f"حجم جدید: {abs(new_size)}"
                )

            elif abs(new_size) < abs(old_size):

                send_message(
                    "🐋 HYPERLIQUID WALLET TRACKER\n"
                    f"📉 کاهش حجم پوزیشن: {coin}\n"
                    f"حجم قبلی: {abs(old_size)}\n"
                    f"حجم جدید: {abs(new_size)}"
                )


# ========== MAIN ==========

if __name__ == "__main__":

    if not BOT_TOKEN or not CHANNEL_ID:
        raise ValueError("Telegram secrets missing")

    print("HYPERLIQUID WALLET TRACKER STARTING")

    previous_positions = get_positions()

    send_message(
        "🐋 HYPERLIQUID WALLET TRACKER\n"
        "✅ ربات فعال شد\n"
        f"👛 آدرس تحت نظر:\n{WALLET}\n"
        f"📊 پوزیشن‌های باز فعلی: "
        f"{len(previous_positions)}"
    )

    start_time = time.time()

    while time.time() - start_time < RUN_SECONDS:

        try:
            current = get_positions()

            notify_changes(previous_positions, current)

            previous_positions = current

            print("Monitoring OK:", len(current), "positions")

        except Exception as e:
            print("Monitoring error:", e)

        time.sleep(CHECK_INTERVAL)

    print("Monitoring cycle finished")
