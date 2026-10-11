import logging

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.constants import ParseMode

from .formatter import montar_caption
from .models import Oferta

log = logging.getLogger("ofertas.poster")


def teclado_oferta(o: Oferta) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Pegar oferta", url=o.url_afiliado)]])


async def postar_oferta(bot: Bot, oferta: Oferta, chat_id: str | int,
                        teclado: InlineKeyboardMarkup | None = None) -> Message:
    caption = montar_caption(oferta)
    markup = teclado or teclado_oferta(oferta)
    if oferta.imagem:
        try:
            return await bot.send_photo(chat_id, oferta.imagem, caption=caption,
                                        parse_mode=ParseMode.HTML, reply_markup=markup)
        except Exception as e:  # imagem recusada pelo Telegram -> cai para texto
            log.warning("send_photo falhou (%s), enviando como texto", e)
    return await bot.send_message(chat_id, caption, parse_mode=ParseMode.HTML,
                                  reply_markup=markup, disable_web_page_preview=True)


async def marcar_esgotado(bot: Bot, chat_id: str | int, message_id: int,
                          motivo: str = "PROMOÇÃO ENCERRADA OU ESGOTADA") -> bool:
    """Edita a mensagem postada no Telegram adicionando aviso de esgotado/expirado."""
    novo_aviso = f"⚠️ <b>[{motivo}]</b> ⚠️\n\n"
    try:
        # Tenta editar como legenda de foto
        await bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=f"{novo_aviso}<i>Esta oferta não está mais disponível no valor anunciado.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=None,
        )
        return True
    except Exception as e_cap:
        try:
            # Tenta editar como mensagem de texto simples
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"{novo_aviso}<i>Esta oferta não está mais disponível no valor anunciado.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=None,
            )
            return True
        except Exception as e_txt:
            log.error("Não foi possível marcar mensagem %s como esgotada: %s / %s", message_id, e_cap, e_txt)
            return False

