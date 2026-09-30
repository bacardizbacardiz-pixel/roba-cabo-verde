            user.get("first_name")
            or user.get("username")
            or "Dalyvis"
        )

        text = (
            message.get("text")
            or message.get("caption")
            or ""
        ).strip()

        photos = message.get("photo", [])

        photo_file_id = None

        if photos:

            photo_file_id = (
                photos[-1].get("file_id")
            )

        replied_to_roba = is_reply_to_roba(
            message
        )

        reply_context = get_reply_context(
            message
        )

        if not text and not photo_file_id:
            return "OK", 200

        thread = threading.Thread(
            target=process_message,
            args=(
                chat_id,
                message_id,
                sender_id,
                name,
                text,
                photo_file_id,
                replied_to_roba,
                reply_context
            ),
            daemon=True
        )

        thread.start()

        return "OK", 200

    except Exception as e:

        print(
            f"WEBHOOK KLAIDA: "
            f"{type(e).__name__}: {e}",
            flush=True
        )

        return "OK", 200


# ============================================================
# WEBHOOK SETUP
# ============================================================

@web.route("/setup-webhook")
def setup_webhook():

    try:

        get_bot_identity()

        result = telegram_api(
            "setWebhook",
            {
                "url": WEBHOOK_URL,
                "drop_pending_updates": True,
                "allowed_updates": [
                    "message",
                    "edited_message"
                ]
            }
        )

        return jsonify({
            "status": "OK",
            "telegram": result
        })

    except Exception as e:

        return jsonify({
            "status": "ERROR",
            "error": str(e)
        }), 500


# ============================================================
# WEBHOOK INFO
# ============================================================

@web.route("/webhook-info")
def webhook_info():

    try:

        result = telegram_api(
            "getWebhookInfo"
        )

        return jsonify(result)

    except Exception as e:

        return jsonify({
            "status": "ERROR",
            "error": str(e)
        }), 500
