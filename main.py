import os
import time
import requests

# ========== CONFIG ==========

MY_WALLET = "0x1f250Df59A777d61Cb8bd043c12970F3AFE4F925"

WALLETS = {
    "MY WALLET": MY_WALLET,

    "WHALE 1": "0x5b5d51203a0f9079f8aeb098a6523a13f298c060",

    "WHALE 2": "0xb83de012dba672c76a7dbbbf3e459cb59d7d6e36",

    "WHALE 3": "0x659ddde484fd9dc313917d5de92a52b6a74a9d63",

    "WHALE 4": "0x87f9cd15f5050a9283b8896300f7c8cf69ece2cf",

    "WHALE 5": "0x45d26f28196d226497130c4bac709d808fed4029",

    "BobbyBigSize": "0x7fdafde5cfb5465924316eced2d3715494c517d1",

    "WHALE 7": "0xb695651daa495f59dd2725c6fe98322d8b51a92d",

    "WHALE 8": "0xdf954bbe619273a56e0cfa90dad8382195dc7d72",

    "WHALE 9": "0xecb63caa47c7c4e77f60f1ce858cf28dc2b82b00",

    "John Wick": "0xfc27136e42af1732ddc9ce2605ea9bff1b959d9d"
}

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

INFO_URL = "https://api.hyperliquid.xyz/info"

CHECK_INTERVAL = 10
RUN_SECONDS = 260

session = requests.Session()


# ========== TELEGRAM ==========

def send_message(message):

    if not BOT_TOKEN or not CHANNEL_ID:
        print("Telegram secrets missing")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        response = session.post(
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

def get_positions(wallet):

    response = session.post(
        INFO_URL,
        json={
            "type": "clearinghouseState",
            "user": wallet
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

        positions[coin] = {
            "size": size,
            "entry": float(p.get("entryPx") or 0),
            "pnl": float(p.get("unrealizedPnl") or 0)
        }

    return positions


# ========== POSITION MONITOR ==========

def notify_changes(name, wallet, old, new):

    coins = set(old.keys()) | set(new.keys())

    for coin in coins:

        before = old.get(coin)
        after = new.get(coin)

        header = (
            "🐋 HYPERLIQUID WHALE TRACKER\n"
            "━━━━━━━━━━━━━━━━\n"
            f"👑 نهنگ: {name}\n"
            f"👛 آدرس: {wallet}\n"
            f"💎 ارز: {coin}\n"
        )

        # OPEN

        if before is None and after is not None:

            side = "🟢 LONG" if after["size"] > 0 else "🔴 SHORT"

            send_message(
                header +
                "🆕 پوزیشن جدید باز شد\n"
                f"📊 جهت: {side}\n"
                f"📦 حجم: {abs(after['size'])}\n"
                f"💰 قیمت ورود: {after['entry']}\n"
                "━━━━━━━━━━━━━━━━"
            )

        # CLOSE

        elif before is not None and after is None:

            send_message(
                header +
                "❌ پوزیشن کاملاً بسته شد\n"
                f"📦 حجم قبلی: {abs(before['size'])}\n"
                f"📊 جهت قبلی: "
                f"{'LONG' if before['size'] > 0 else 'SHORT'}\n"
                "━━━━━━━━━━━━━━━━"
            )

        # CHANGE

        elif before is not None and after is not None:

            old_size = before["size"]
            new_size = after["size"]

            if old_size * new_size < 0:

                send_message(
                    header +
                    "🔄 تغییر جهت پوزیشن\n"
                    f"جهت جدید: "
                    f"{'🟢 LONG' if new_size > 0 else '🔴 SHORT'}\n"
                    f"حجم جدید: {abs(new_size)}"
                )

            elif abs(new_size) > abs(old_size):

                send_message(
                    header +
                    "📈 افزایش حجم پوزیشن\n"
                    f"حجم قبلی: {abs(old_size)}\n"
                    f"حجم جدید: {abs(new_size)}"
                )

            elif abs(new_size) < abs(old_size):

                send_message(
                    header +
                    "📉 کاهش حجم پوزیشن\n"
                    f"حجم قبلی: {abs(old_size)}\n"
                    f"حجم جدید: {abs(new_size)}"
                )


# ========== MAIN ==========

if __name__ == "__main__":

    if not BOT_TOKEN or not CHANNEL_ID:
        raise ValueError("Telegram secrets missing")

    print("HYPERLIQUID MULTI WHALE TRACKER STARTING")

    previous = {}

    active = {}

    # INITIAL SCAN

    for name, wallet in WALLETS.items():

        try:

            positions = get_positions(wallet)

            previous[name] = positions
            active[name] = wallet

            print(name, "OK:", len(positions))

        except Exception as e:

            print(name, "ERROR:", e)

    send_message(
        "🐋 HYPERLIQUID WHALE TRACKER PRO\n"
        "━━━━━━━━━━━━━━━━\n"
        "✅ سیستم چندنهنگی فعال شد\n"
        f"👑 تعداد کیف پول‌ها: {len(active)}\n"
        f"📊 کیف پول‌های متصل: {len(active)}\n"
        f"📈 پوزیشن‌های باز: "
        f"{sum(len(p) for p in previous.values())}\n"
        "━━━━━━━━━━━━━━━━"
    )

    start_time = time.time()

    while time.time() - start_time < RUN_SECONDS:

        for name, wallet in active.items():

            try:

                current = get_positions(wallet)

                notify_changes(
                    name,
                    wallet,
                    previous[name],
                    current
                )

                previous[name] = current

                print(
                    "MONITORING:",
                    name,
                    len(current)
                )

            except Exception as e:

                print(name, "ERROR:", e)

        time.sleep(CHECK_INTERVAL)

    print("MONITORING FINISHED")
