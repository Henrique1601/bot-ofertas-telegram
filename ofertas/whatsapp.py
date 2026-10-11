"""Módulo de cross-posting para WhatsApp (Canais e Grupos).

Suporta APIs modernas de WhatsApp (Evolution API, Z-API ou compatíveis).
Totalmente opcional: só envia se WHATSAPP_API_URL e WHATSAPP_CHATS estiverem configurados.
"""
import logging
import os
import re
import requests

from .config import config
from .formatter import preco_br
from .models import Oferta

log = logging.getLogger("ofertas.whatsapp")


def _formatar_caption_whatsapp(o: Oferta) -> str:
    """Formata a legenda para o padrão markdown do WhatsApp (*bold*, ~strike~, _italic_)."""
    linhas = []

    if o.is_super_desconto:
        linhas.append("🚨 *SUPER OFERTA / POSSÍVEL BUG DE PREÇO* 🚨\n")

    if o.is_menor_preco:
        linhas.append("📉 *MENOR PREÇO HISTÓRICO REGISTRADO!* \n")

    linhas.append(f"🔥 *{o.titulo[:160]}*")
    linhas.append("")

    if o.preco and o.preco_original and o.preco_original > o.preco:
        linhas.append(f"❌ De: ~{preco_br(o.preco_original)}~")
        selo = f"  🔻 *-{o.desconto}%*" if o.desconto else ""
        linhas.append(f"✅ Por: *{preco_br(o.preco)}*{selo}")
    elif o.preco:
        selo = f"  🔻 *-{o.desconto}%*" if o.desconto else ""
        linhas.append(f"✅ *{preco_br(o.preco)}*{selo}")

    if o.cupom:
        linhas.append(f"🎟️ Cupom: `{o.cupom.strip().upper()}`")

    if o.destaques_ia:
        linhas.append("")
        linhas.append("✨ *Destaques:*")
        for d in o.destaques_ia:
            linhas.append(f"• {d}")

    if o.extra:
        linhas.append(o.extra)

    linhas.append("")
    linhas.append(f"🛒 *Pegar oferta aqui:* {o.url_afiliado}")

    return "\n".join(linhas)


def postar_whatsapp(o: Oferta) -> int:
    """Dispara a oferta para todos os grupos/canais de WhatsApp configurados. Retorna total de envios bem sucedidos."""
    api_url = getattr(config, "whatsapp_api_url", "") or os.getenv("WHATSAPP_API_URL", "").strip().rstrip("/")
    api_key = getattr(config, "whatsapp_api_key", "") or os.getenv("WHATSAPP_API_KEY", "").strip()
    instancia = getattr(config, "whatsapp_instance", "") or os.getenv("WHATSAPP_INSTANCE", "ofertas").strip()
    chats_raw = getattr(config, "whatsapp_chats", "") or os.getenv("WHATSAPP_CHATS", "").strip()

    if not api_url or not chats_raw:
        return 0

    chats = [c.strip() for c in chats_raw.split(",") if c.strip()]
    if not chats:
        return 0

    caption = _formatar_caption_whatsapp(o)
    headers = {"apikey": api_key, "Content-Type": "application/json"}
    sucessos = 0

    for chat_id in chats:
        try:
            if o.imagem:
                # Endpoint padrão Evolution API sendMedia
                url = f"{api_url}/message/sendMedia/{instancia}"
                payload = {
                    "number": chat_id,
                    "media": o.imagem,
                    "mediatype": "image",
                    "caption": caption
                }
            else:
                url = f"{api_url}/message/sendText/{instancia}"
                payload = {
                    "number": chat_id,
                    "text": caption
                }

            r = requests.post(url, json=payload, headers=headers, timeout=15)
            if r.status_code in (200, 201):
                sucessos += 1
            else:
                log.warning("WhatsApp envio falhou para %s (HTTP %s): %s", chat_id, r.status_code, r.text[:200])
        except Exception as e:
            log.error("Erro ao enviar oferta para WhatsApp %s: %s", chat_id, e)

    if sucessos > 0:
        log.info("WhatsApp: oferta postada com sucesso em %d chat(s)", sucessos)
    return sucessos
