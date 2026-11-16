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

MIN_POSITION_USD = 10_000_000

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


# ========== MARKET PRICES ==========

def get_market_prices():

    response = session.post(
        INFO_URL,
        json={"type": "metaAndAssetCtxs"},
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    meta = data[0]
    contexts = data[1]

    prices = {}

    for asset, context in zip(meta["universe"], contexts):

        coin = asset["name"]
        mark_price = float(context.get("markPx") or 0)

        if mark_price > 0:
            prices[coin] = mark_price

    return prices


# ========== POSITIONS ==========

def get_positions(wallet, prices):

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

        mark_price = prices.get(coin, 0)

        if mark_price <= 0:
            print("MARK PRICE MISSING:", coin)
            continue

        position_value = abs(size) * mark_price

        positions[coin] = {
            "size": size,
            "entry": float(p.get("entryPx") or 0),
            "pnl": float(p.get("unrealizedPnl") or 0),
            "mark": mark_price,
            "value": position_value
        }

    return positions


# ========== NOTIFICATIONS ==========

def notify_changes(name, wallet, old, current):

    # فقط پوزیشن‌های بالای آستانه
    qualified = {
        coin: p for coin, p in current.items()
        if p["value"] >= MIN_POSITION_USD
    }

    coins = set(old.keys()) | set(qualified.keys())

    for coin in coins:

        before = old.get(coin)
        after = qualified.get(coin)
        raw_after = current.get(coin)

        header = (
            "🐋 HYPERLIQUID WHALE TRACKER PRO\n"
            "━━━━━━━━━━━━━━━━\n"
            f"👑 نهنگ: {name}\n"
            f"👛 آدرس: {wallet}\n"
            f"💎 ارز: {coin}\n"
        )

        # NEW QUALIFIED POSITION

        if before is None and after is not None:

            side = "🟢 LONG" if after["size"] > 0 else "🔴 SHORT"

            send_message(
                header +
                "🚨 پوزیشن بالای ۱۰ میلیون دلار شناسایی شد\n"
                f"📊 جهت: {side}\n"
                f"📦 حجم: {abs(after['size'])}\n"
                f"💵 ارزش پوزیشن: ${after['value']:,.0f}\n"
                f"💰 قیمت ورود: {after['entry']}\n"
                f"📍 قیمت لحظه‌ای: {after['mark']}\n"
                "━━━━━━━━━━━━━━━━"
            )

        # CLOSED OR DROPPED BELOW THRESHOLD

        elif before is not None and after is None:

            if raw_after is None:

                status = "❌ پوزیشن کاملاً بسته شد"

            else:

                status = "⚠️ ارزش پوزیشن به زیر ۱۰ میلیون دلار رسید"

            send_message(
                header +
                status + "\n"
                f"💵 ارزش قبلی: ${before['value']:,.0f}\n"
                "━━━━━━━━━━━━━━━━"
            )

        # POSITION CHANGES

        elif before is not None and after is not None:

            old_size = before["size"]
            new_size = after["size"]

            if old_size * new_size < 0:

                event = "🔄 تغییر جهت پوزیشن"

            elif abs(new_size) > abs(old_size):

                event = "📈 افزایش حجم پوزیشن"

            elif abs(new_size) < abs(old_size):

                event = "📉 کاهش حجم پوزیشن"

            else:
                continue

            send_message(
                header +
                event + "\n"
                f"📦 حجم قبلی: {abs(old_size)}\n"
                f"📦 حجم جدید: {abs(new_size)}\n"
                f"💵 ارزش جدید: ${after['value']:,.0f}\n"
                f"📊 جهت جدید: "
                f"{'🟢 LONG' if new_size > 0 else '🔴 SHORT'}\n"
                "━━━━━━━━━━━━━━━━"
            )

    return qualified


# ========== MAIN ==========

if __name__ == "__main__":

    if not BOT_TOKEN or not CHANNEL_ID:
        raise ValueError("Telegram secrets missing")

    print("HYPERLIQUID WHALE TRACKER PRO STARTING")

    previous = {}
    active = {}

    try:
        prices = get_market_prices()
    except Exception as e:
        raise RuntimeError(f"Market price error: {e}")

    # INITIAL SCAN

    for name, wallet in WALLETS.items():

        try:

            positions = get_positions(wallet, prices)

            previous[name] = {
                coin: p for coin, p in positions.items()
                if p["value"] >= MIN_POSITION_USD
            }

            active[name] = wallet

            print(
                name,
                "CONNECTED:",
                len(positions),
                "positions;",
                len(previous[name]),
                "above threshold"
            )

        except Exception as e:

            print(name, "ERROR:", e)

    send_message(
        "🐋 HYPERLIQUID WHALE TRACKER PRO\n"
        "━━━━━━━━━━━━━━━━\n"
        "✅ سیستم چندنهنگی فعال شد\n"
        f"👑 کیف
