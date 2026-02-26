import httpx
from loguru import logger

async def send_discord_notification(webhook_url: str, message: str):
    if not webhook_url:
        logger.warning("Discord webhook URL not configured. Skipping notification.")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json={"content": message}
            )
            response.raise_for_status()
            logger.info("Discord notification sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")

async def send_client_webhook(webhook_url: str, payload: dict):
    if not webhook_url:
        return
        
    # Auto-format payload if the user provided a Discord webhook URL as their client webhook
    if "discord.com/api/webhooks" in webhook_url:
        import json
        payload_str = json.dumps(payload, indent=2)
        if len(payload_str) > 1800:
            payload_str = payload_str[:1800] + "\n...[Texte tronqué pour Discord]..."
        payload = {"content": f"**Nouvelle extraction terminée**\n```json\n{payload_str}\n```"}
        
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload
            )
            response.raise_for_status()
            logger.info(f"Client webhook sent successfully to {webhook_url}")
    except Exception as e:
        logger.error(f"Failed to send client webhook to {webhook_url}: {e}")
