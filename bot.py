#!/usr/bin/env python3
"""
adhahiGwi_bot — Wilaya Quota Monitor
Polls adhahi.dz/api/v1/public/wilaya-quotas every 30 seconds.

TEST_MODE       = True  → alerts when a wilaya becomes UNAVAILABLE (available: false)
TEST_MODE       = False → alerts when a wilaya becomes AVAILABLE   (available: true)
SEND_TEST_MSGS  = True  → sends a heartbeat message every 10s (for testing)
SEND_TEST_MSGS  = False → silent, no heartbeat (production)
"""

import asyncio
import logging
import requests
from telegram import Bot
from telegram.error import TelegramError

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
BOT_TOKEN       = "8609649170:AAEt2yiN9X6DSRm-v-dvxrDx9fYGXa0_S0w"
CHATS_ID        = [2006244631, 1239935927, 1475463780]
API_URL         = "https://adhahi.dz/api/v1/public/wilaya-quotas"
INTERVAL        = 30           # seconds between polls

# ── TEST MODE ──────────────────────────────────
# True  → alert when available == False  (testing: easier to trigger)
# False → alert when available == True   (production behaviour)
TEST_MODE       = True

# ── HEARTBEAT TEST MESSAGES ────────────────────
# True  → sends "still alive" message every 10s
# False → disabled (use in production)
SEND_TEST_MSGS  = True
TEST_MSG_INTERVAL = 10         # seconds between heartbeat messages

# ── Wilayas to watch (hardcoded codes) ────────
WATCHED_CODES = [
    "01", "02", "03", "04", "05",
    "06", "07", "08", "09", "10",
    "11", "12", "13", "14", "15",
    "16", "17", "18", "19", "20",
    "21", "22", "23", "24", "25",
    "26", "27", "28", "29", "30",
    "31", "32", "33", "34", "35",
    "36", "37", "38", "39", "40",
    "41", "42", "43", "44", "45",
    "46", "47", "48", "49", "50",
    "51", "52", "53", "54", "55",
    "56", "57", "58", "59", "60",
    "61", "62", "63", "64", "65",
    "66", "67", "68", "69",
]

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  STATE
# ─────────────────────────────────────────────
last_state: dict[str, bool | None] = {code: None for code in WATCHED_CODES}


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def fetch_quotas() -> list[dict] | None:
    try:
        resp = requests.get(API_URL, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        log.error("Failed to fetch quotas: %s", e)
        return None


def build_message(wilaya: dict, trigger_value: bool) -> str:
    code    = wilaya["wilayaCode"]
    name_ar = wilaya.get("wilayaNameAr", "")
    name_fr = wilaya.get("wilayaNameFr", "")

    if trigger_value:
        emoji  = "✅"
        status = "DISPONIBLE"
        label  = "Un poste est maintenant ouvert !"
    else:
        emoji  = "🔴"
        status = "INDISPONIBLE"
        label  = "Le poste vient de fermer."

    mode_tag = "🧪 TEST MODE\n" if TEST_MODE else ""

    return (
        f"IF YOU SEE THIS MESSAGE, 3Ayti l Imad 5okm :)\n"
        f"{mode_tag}"
        f"{emoji} Wilaya {code} — {name_fr} / {name_ar}\n"
        f"Statut : {status}\n"
        f"{label}"
    )


async def broadcast(bot: Bot, message: str) -> None:
    """Send a message to all chat IDs in CHATS_ID."""
    for chat_id in CHATS_ID:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            log.info("Sent to %s: %s", chat_id, message.splitlines()[0])
        except TelegramError as e:
            log.error("Telegram error to %s: %s", chat_id, e)


# ─────────────────────────────────────────────
#  HEARTBEAT TASK  (runs independently)
# ─────────────────────────────────────────────
async def heartbeat_loop(bot: Bot) -> None:
    """Sends a test message every TEST_MSG_INTERVAL seconds if SEND_TEST_MSGS is True."""
    counter = 0
    while True:
        await asyncio.sleep(TEST_MSG_INTERVAL)
        counter += 1
        msg = f"🟡 Heartbeat #{counter} — bot en vie, polling toutes les {INTERVAL}s"
        await broadcast(bot, msg)
        log.info("Heartbeat #%d sent", counter)


# ─────────────────────────────────────────────
#  MAIN POLL LOOP
# ─────────────────────────────────────────────
async def poll_loop(bot: Bot) -> None:
    watched_set = set(WATCHED_CODES)

    while True:
        data = fetch_quotas()

        if data is not None:
            for wilaya in data:
                code = wilaya.get("wilayaCode")
                if code not in watched_set:
                    continue

                current  = wilaya.get("available")
                previous = last_state.get(code)

                trigger_value = False if TEST_MODE else True

                if current == trigger_value and previous != trigger_value:
                    msg = build_message(wilaya, trigger_value)
                    await broadcast(bot, msg)

                last_state[code] = current

        await asyncio.sleep(INTERVAL)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
async def main() -> None:
    bot = Bot(token=BOT_TOKEN)

    mode_label = "🧪 TEST MODE (alerte si indisponible)" if TEST_MODE else "🚀 PRODUCTION (alerte si disponible)"
    heartbeat_label = f"💓 Heartbeat toutes les {TEST_MSG_INTERVAL}s activé" if SEND_TEST_MSGS else "💤 Heartbeat désactivé"

    startup_msg = (
        f"🤖 adhahiGwi_bot démarré\n"
        f"Mode : {mode_label}\n"
        f"{heartbeat_label}\n"
        f"Wilayas surveillées : {len(WATCHED_CODES)}\n"
        f"Intervalle de polling : toutes les {INTERVAL}s"
    )
    await broadcast(bot, startup_msg)
    log.info("Bot started — TEST_MODE=%s, SEND_TEST_MSGS=%s", TEST_MODE, SEND_TEST_MSGS)

    tasks = [asyncio.create_task(poll_loop(bot))]

    if SEND_TEST_MSGS:
        tasks.append(asyncio.create_task(heartbeat_loop(bot)))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())