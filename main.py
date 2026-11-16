import os
import time
import requests

# ========== CONFIG ==========

WALLETS = {
    "WALLET 1": "0x1f250Df59A777d61Cb8bd043c12970F3AFE4F925",

    "WALLET 2": "0xfb1898bb5955fdd11704e397104c6a0e0725eb17"
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
        print("TELEGRAM SENT")

    except Exception as e:
        print("TELEGRAM ERROR:", e)


# ========== HYPERLIQUID API ==========

def api_request(payload):

    response = session.post(
        INFO_URL,
        json=payload,
        timeout=20
    )

    response.raise_for_status()

    return response.json()


# ========== MARKET PRICES ==========

def get_market_prices():

    data = api_request({
        "type": "metaAndAssetCtxs"
    })

    meta = data[0]
    contexts = data[1]

    prices = {}

    for asset, context in zip(
        meta["universe"],
        contexts
    ):

        coin = asset["name"]

        mark_price = float(
            context.get("markPx") or 0
        )

        if mark_price > 0:
            prices[coin] = mark_price

    return prices


# ========== GET POSITIONS ==========

def get_positions(wallet, prices):

    data = api_request({
        "type": "clearinghouseState",
        "user": wallet
    })

    positions = {}

    for item in data.get("assetPositions", []):

        p = item["position"]

        coin = p["coin"]

        size = float(p["szi"])

        if size == 0:
            continue

        mark_price = prices.get(coin)

        if not mark_price:
            raise ValueError(
                f"MARK PRICE MISSING: {coin}"
            )

        position_value = abs(size) * mark_price

        positions[coin] = {
            "size": size,
            "entry": float(p.get("entryPx") or 0),
            "pnl": float(p.get("unrealizedPnl") or 0),
            "mark": mark_price,
            "value": position_value
        }

    return positions


# ========== POSITION MONITOR ==========

def notify_changes(name, wallet, old, current):

    qualified = {
        coin: p
        for coin, p in current.items()
        if p["value"] >= MIN_POSITION_USD
    }

    coins = set(old.keys()) | set(qualified.keys())

    for coin in coins:

        before = old.get(coin)

        after = qualified.get(coin)

        raw_after = current.get(coin)

        header = (
            "🐋 HYPERLIQUID WHALE TRACKER PRO\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"👑 کیف پول: {name}\n"
            f"👛 آدرس: {wallet}\n"
            f"💎 ارز: {coin}\n"
        )

        # NEW POSITION

        if before is None and after is not None:

            side = (
                "🟢 LONG"
                if after["size"] > 0
                else "🔴 SHORT"
            )

            send_message(
                header +
                "🚨 پوزیشن جدید بالای ۱۰ میلیون دلار\n"
                f"📊 جهت: {side}\n"
                f"📦 حجم: {abs(after['size'])}\n"
                f"💵 ارزش پوزیشن: ${after['value']:,.0f}\n"
                f"💰 قیمت ورود: {after['entry']}\n"
                f"📍 قیمت لحظه‌ای: {after['mark']}\n"
                f"📈 سود شناور: ${after['pnl']:,.2f}\n"
                "━━━━━━━━━━━━━━━━━━"
            )

        # CLOSE OR BELOW THRESHOLD

        elif before is not None and after is None:

            if raw_after is None:
                status = "❌ پوزیشن کاملاً بسته شد"
            else:
                status = "⚠️ ارزش پوزیشن به زیر ۱۰ میلیون دلار رسید"

            send_message(
                header +
                status + "\n"
                f"💵 ارزش قبلی: ${before['value']:,.0f}\n"
                "━━━━━━━━━━━━━━━━━━"
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

            side = (
                "🟢 LONG"
                if new_size > 0
                else "🔴 SHORT"
            )

            send_message(
                header +
                event + "\n"
                f"📊 جهت جدید: {side}\n"
                f"📦 حجم قبلی: {abs(old_size)}\n"
                f"📦 حجم جدید: {abs(new_size)}\n"
                f"💵 ارزش قبلی: ${before['value']:,.0f}\n"
                f"💵 ارزش جدید: ${after['value']:,.0f}\n"
                f"📈 سود شناور: ${after['pnl']:,.2f}\n"
                "━━━━━━━━━━━━━━━━━━"
            )

    return qualified


# ========== MAIN ==========

if __name__ == "__main__":

    if not BOT_TOKEN or not CHANNEL_ID:
        raise ValueError("Telegram secrets missing")

    print("HYPERLIQUID TWO WALLET TRACKER STARTING")

    previous = {}
    active = {}

    # INITIAL MARKET DATA

    prices = get_market_prices()

    # INITIAL WALLET SCAN

    for name, wallet in WALLETS.items():

        try:

            positions = get_positions(wallet, prices)

            previous[name] = {
                coin: p
                for coin, p in positions.items()
                if p["value"] >= MIN_POSITION_USD
            }

            active[name] = wallet

            print(
                name,
                "CONNECTED:",
                len(positions),
                "POSITIONS",
                "| QUALIFIED:",
                len(previous[name])
            )

        except Exception as e:

            print(name, "ERROR:", e)

    # START MESSAGE

    send_message(
        "🐋 HYPERLIQUID WHALE TRACKER PRO\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "✅ سیستم فعال شد\n"
        "👑 تعداد کیف پول‌ها: 2\n"
        f"📡 کیف پول‌های متصل: {len(active)}\n"
        f"💰 حداقل ارزش پوزیشن: ${MIN_POSITION_USD:,.0f}\n"
        "📊 فیلتر ارزش پوزیشن فعال است\n"
        "━━━━━━━━━━━━━━━━━━"
    )

    # MONITORING LOOP

    start_time = time.time()

    while time.time() - start_time < RUN_SECONDS:

        try:
            prices = get_market_prices()

        except Exception as e:

            print("PRICE UPDATE ERROR:", e)

            time.sleep(CHECK_INTERVAL)

            continue

        for name, wallet in active.items():

            try:

                current = get_positions(wallet, prices)

                previous[name] = notify_changes(
                    name,
                    wallet,
                    previous[name],
                    current
                )

                print(
                    "MONITORING:",
                    name,
                    "QUALIFIED:",
                    len(previous[name])
                )

            except Exception as e:

                print(name, "ERROR:", e)

        time.sleep(CHECK_INTERVAL)

    print("MONITORING FINISHED")
