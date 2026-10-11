"""Bot do Telegram: posta os ciclos automáticos e, no privado, converte
qualquer link colado (ML/Shopee/Amazon) em post com o seu link de afiliado.
"""
import asyncio
import logging
import secrets

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

from . import db, pipeline
from .config import config
from .models import Oferta
from .sources import detectar_fonte
from .telegram_poster import postar_oferta
from .utils import extrair_urls

log = logging.getLogger("ofertas.bot")

_pendentes: dict[str, Oferta] = {}


async def _cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 <b>Bot de Ofertas Multi-Plataforma</b>\n\n"
        "• Cole aqui um link do <b>Mercado Livre, Shopee, Amazon, AliExpress ou Magalu</b> e eu preparo o post com seu link de afiliado e cupom.\n"
        "• <b>Radar de Desejos:</b> Cadastre alertas para ser avisado no privado quando um produto baixar de preço:\n"
        "  └ <code>/desejo air fryer 250</code> ou <code>/desejo fone bluetooth</code>\n"
        "  └ <code>/meusdesejos</code> — veja seus alertas ativos\n"
        "  └ <code>/removerdesejo &lt;id&gt;</code> — remove um alerta\n\n"
        "• <b>Comandos de Administrador:</b>\n"
        "• /id — mostra o ID deste chat ou canal\n"
        "• /ciclo — roda um ciclo de busca agora\n"
        "• /esgotado &lt;link_ou_id&gt; — marca uma oferta postada como esgotada no canal\n"
        "• /status — situação do bot",
        parse_mode="HTML",
    )


async def _cmd_desejo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Permite qualquer inscrito cadastrar um desejo de compra (ex: /desejo air fryer 250)."""
    args = ctx.args or []
    if not args:
        await update.message.reply_text(
            "🔔 <b>Como usar o Radar de Ofertas:</b>\n\n"
            "Envie: <code>/desejo &lt;produto&gt; [preço máximo]</code>\n\n"
            "Exemplos:\n"
            "• <code>/desejo air fryer 250</code> (alerta quando custar até R$ 250)\n"
            "• <code>/desejo fone bluetooth</code> (alerta para qualquer preço)",
            parse_mode="HTML"
        )
        return

    preco_max = None
    try:
        ultimo = args[-1].replace(",", ".")
        preco_max = float(ultimo)
        termos = args[:-1]
    except ValueError:
        termos = args

    termo_busca = " ".join(termos).strip()
    if not termo_busca:
        await update.message.reply_text("Informe o nome do produto que deseja monitorar.")
        return

    did = db.adicionar_desejo(update.effective_user.id, termo_busca, preco_max)
    texto_preco = f" por até <b>R$ {preco_max:.2f}</b>" if preco_max else " em qualquer preço"
    await update.message.reply_text(
        f"🎯 <b>Alerta #{did} cadastrado!</b>\n"
        f"Assim que o robô encontrar <b>{termo_busca}</b>{texto_preco}, você será avisado no privado aqui no Telegram! 🔔",
        parse_mode="HTML"
    )


async def _cmd_meusdesejos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lista = db.listar_desejos_usuario(update.effective_user.id)
    if not lista:
        await update.message.reply_text(
            "Você não tem alertas de desejos ativos no momento.\n"
            "Cadastre um com: <code>/desejo &lt;produto&gt; [preço]</code>",
            parse_mode="HTML"
        )
        return

    linhas = ["📋 <b>Seus Alertas de Ofertas Ativos:</b>\n"]
    for d in lista:
        preco_str = f"até R$ {d['preco_max']:.2f}" if d.get('preco_max') else "qualquer valor"
        linhas.append(f"• <b>#{d['id']}</b> — {d['termo']} ({preco_str})")
    linhas.append("\nPara remover um alerta, use: <code>/removerdesejo &lt;id&gt;</code>")
    await update.message.reply_text("\n".join(linhas), parse_mode="HTML")


async def _cmd_removerdesejo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Informe o ID do alerta para remover. Ex: <code>/removerdesejo 1</code>", parse_mode="HTML")
        return
    did = int(args[0])
    sucesso = db.remover_desejo(did, update.effective_user.id)
    if sucesso:
        await update.message.reply_text(f"✅ Alerta #{did} removido com sucesso!")
    else:
        await update.message.reply_text("❌ Alerta não encontrado ou não pertence a você.")



async def _cmd_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        f"Este chat: `{update.effective_chat.id}`\n"
        f"Seu user id: `{update.effective_user.id}`\n\n"
        "Para descobrir o id do canal, encaminhe aqui qualquer post dele.",
        parse_mode="Markdown",
    )


async def _cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    fontes = [nome for nome, f in (("Mercado Livre", config.fonte_ml),
                                   ("Shopee", config.fonte_shopee),
                                   ("Amazon", config.fonte_amazon),
                                   ("AliExpress", config.fonte_aliexpress),
                                   ("Magalu", config.fonte_magalu)) if f.get("ativa")]
    canais_info = f"{config.chat_id}" + (f" (+{len(config.canais_extras)} canais extras)" if config.canais_extras else "")
    await update.message.reply_text(
        f"📊 {db.total_postadas()} ofertas postadas até agora\n"
        f"📢 Canal principal: {canais_info}\n"
        f"🔎 Fontes automáticas ativas: {', '.join(fontes) or 'nenhuma'}\n"
        f"⏱ Ciclo a cada {config.intervalo_minutos} min, "
        f"máx. {config.max_posts_por_ciclo} posts por ciclo\n"
        f"🎯 Desconto mínimo: {config.desconto_minimo}%\n"
        f"🕒 Horário ativo: {config.horario_ativo or '24 horas'}"
    )


def _e_dono(update: Update) -> bool:
    return bool(config.owner_id) and update.effective_user.id == config.owner_id


async def _cmd_ciclo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _e_dono(update):
        return
    await update.message.reply_text("🔄 Rodando um ciclo de busca...")
    postadas = await pipeline.executar_ciclo(ctx.bot)
    await update.message.reply_text(f"✅ Ciclo terminou: {postadas} oferta(s) postada(s).")


async def _cmd_esgotado(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _e_dono(update):
        return
    args = ctx.args or []
    if not args:
        await update.message.reply_text("Uso: `/esgotado <id_ou_link>` (ex: `/esgotado MLB123456` ou `/esgotado https://...`)", parse_mode="Markdown")
        return
    alvo = args[0].strip()
    uid = alvo
    fonte = detectar_fonte(alvo)
    if fonte:
        # Se for link, tenta achar o UID
        for p in ("mercadolivre", "amazon", "shopee", "aliexpress", "magalu"):
            item = db.obter_postada(f"{p}:{alvo}")
            if item:
                uid = f"{p}:{alvo}"
                break
    
    registro = db.obter_postada(uid)
    if not registro or not registro.get("message_id") or not registro.get("chat_id"):
        # Tenta busca parcial por UID
        with db._conn() as c:
            row = c.execute("SELECT uid, chat_id, message_id FROM postadas WHERE uid LIKE ? OR titulo LIKE ? LIMIT 1",
                            (f"%{alvo}%", f"%{alvo}%")).fetchone()
        if row and row[1] and row[2]:
            registro = {"uid": row[0], "chat_id": row[1], "message_id": row[2]}
        else:
            await update.message.reply_text("❌ Não encontrei o registro dessa postagem com ID no banco.")
            return

    from .telegram_poster import marcar_esgotado
    sucesso = await marcar_esgotado(ctx.bot, registro["chat_id"], registro["message_id"])
    if sucesso:
        await update.message.reply_text(f"✅ Oferta `{registro.get('uid')}` marcada como esgotada no canal!", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Falha ao editar a mensagem no canal.")



async def _receber_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not config.owner_id:
        await update.message.reply_text(
            "⚠️ Defina TELEGRAM_OWNER_ID no .env para usar o conversor.\n"
            f"Seu user id é `{update.effective_user.id}`.", parse_mode="Markdown")
        return
    if not _e_dono(update):
        return

    msg = update.effective_message
    texto_completo = msg.text or msg.caption or ""
    urls = extrair_urls(texto_completo)
    fonte = url = None
    for u in urls:
        fonte = detectar_fonte(u)
        if fonte:
            url = u
            break
    if not fonte:
        await update.message.reply_text("Não reconheci nenhum link de ML, Shopee, Amazon, AliExpress ou Magalu aí. 🤔")
        return

    aviso = await update.message.reply_text("🔎 Convertendo, um instante...")
    try:
        oferta = await asyncio.to_thread(fonte.converter, url)
        # Se a mensagem original do usuário continha um cupom escrito manualmente, aproveita
        from .utils import extrair_cupom_texto
        cupom_msg = extrair_cupom_texto(texto_completo)
        if cupom_msg and not oferta.cupom:
            oferta.cupom = cupom_msg
    except Exception as e:
        await aviso.edit_text(f"❌ Não consegui converter: {e}")
        return
    await aviso.delete()

    token = secrets.token_hex(4)
    _pendentes[token] = oferta
    teclado = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Pegar oferta", url=oferta.url_afiliado)],
        [InlineKeyboardButton("✅ Postar no canal", callback_data=f"post:{token}"),
         InlineKeyboardButton("🗑 Descartar", callback_data=f"drop:{token}")],
    ])
    await postar_oferta(ctx.bot, oferta, update.effective_chat.id, teclado=teclado)


async def _receber_forward(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    texto = msg.text or msg.caption or ""
    if any(detectar_fonte(u) for u in extrair_urls(texto)):
        await _receber_link(update, ctx)  # encaminhou uma oferta -> converte normalmente
        return
    origem = getattr(msg, "forward_origin", None)
    chat_origem = getattr(origem, "chat", None)
    if chat_origem:
        await msg.reply_text(
            f"📢 Id desse canal/grupo: `{chat_origem.id}`\n"
            "É o valor de TELEGRAM_CHAT_ID no .env.",
            parse_mode="Markdown",
        )
    else:
        await msg.reply_text(
            "Não consegui ver de onde veio — encaminhe direto do canal, sem intermediários."
        )


async def _callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query

    # Tratamento de Reações Interativas nos Posts (🔥 / 👎)
    if q.data.startswith("voto:"):
        partes = q.data.split(":")
        if len(partes) >= 4:
            tipo, plat, id_curto = partes[1], partes[2], partes[3]
            uid = f"{plat}:{id_curto}"
            fogo, caro = db.votar_reacao(uid, tipo, q.from_user.id)

            # Reconstrói teclado com as novas contagens mantendo o link de compra existente
            link_compra = None
            if q.message.reply_markup and q.message.reply_markup.inline_keyboard:
                primeira_linha = q.message.reply_markup.inline_keyboard[0]
                if primeira_linha:
                    link_compra = primeira_linha[0].url

            btn_fogo = f"🔥 Valeu ({fogo})" if fogo > 0 else "🔥 Valeu"
            btn_caro = f"👎 Caro ({caro})" if caro > 0 else "👎 Caro"

            novos_botoes = []
            if link_compra:
                novos_botoes.append([InlineKeyboardButton("🛒 Pegar oferta", url=link_compra)])
            novos_botoes.append([
                InlineKeyboardButton(btn_fogo, callback_data=f"voto:fogo:{plat}:{id_curto}"),
                InlineKeyboardButton(btn_caro, callback_data=f"voto:caro:{plat}:{id_curto}"),
            ])

            try:
                await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(novos_botoes))
            except Exception:
                pass  # sem alteração se o clique foi idêntico

            msg_toast = "Voto registrado! 🔥" if tipo == "fogo" else "Feedback registrado! 👎"
            await q.answer(msg_toast)
            return

    await q.answer()
    acao, _, token = q.data.partition(":")
    oferta = _pendentes.pop(token, None)

    async def _status(texto: str):
        if q.message.photo:
            await q.edit_message_caption((q.message.caption or "") + f"\n\n{texto}")
        else:
            await q.edit_message_text((q.message.text or "") + f"\n\n{texto}")

    if not oferta:
        await _status("⚠️ Essa prévia expirou — mande o link de novo.")
        return
    if acao == "post":
        canais = [config.chat_id] + [c for c in config.canais_extras if c != config.chat_id]
        msg_principal = None
        for chat in canais:
            try:
                msg = await postar_oferta(ctx.bot, oferta, chat)
                if chat == config.chat_id:
                    msg_principal = msg
            except Exception as e:
                log.error("Falha ao postar no canal %s: %s", chat, e)
        
        db.registrar(oferta, chat_id=config.chat_id, message_id=msg_principal.message_id if msg_principal else None)
        await _status("✅ Postada no canal!")
    else:
        await _status("🗑 Descartada.")


async def _job_ciclo(ctx: ContextTypes.DEFAULT_TYPE):
    try:
        await pipeline.executar_ciclo(ctx.bot)
    except Exception as e:
        log.exception("Ciclo automático falhou")
        await pipeline.avisar_dono(ctx.bot, f"⚠️ O ciclo automático falhou: {type(e).__name__}: {e}")


def rodar():
    if not config.bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN não configurado — veja o README (passo 1).")

    app = Application.builder().token(config.bot_token).build()
    app.add_handler(CommandHandler("start", _cmd_start))
    app.add_handler(CommandHandler("id", _cmd_id))
    app.add_handler(CommandHandler("status", _cmd_status))
    app.add_handler(CommandHandler("ciclo", _cmd_ciclo))
    app.add_handler(CommandHandler("esgotado", _cmd_esgotado))
    app.add_handler(CommandHandler("encerrar", _cmd_esgotado))
    app.add_handler(CommandHandler("desejo", _cmd_desejo))
    app.add_handler(CommandHandler("meusdesejos", _cmd_meusdesejos))
    app.add_handler(CommandHandler("removerdesejo", _cmd_removerdesejo))
    app.add_handler(CallbackQueryHandler(_callback))
    app.add_handler(MessageHandler(filters.FORWARDED & filters.ChatType.PRIVATE, _receber_forward))
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.CAPTION) & filters.ChatType.PRIVATE & ~filters.COMMAND,
        _receber_link))


    tem_fonte = any(f.get("ativa") for f in
                    (config.fonte_ml, config.fonte_shopee, config.fonte_amazon,
                     config.fonte_aliexpress, config.fonte_magalu))
    if tem_fonte and config.intervalo_minutos > 0 and config.chat_id:
        app.job_queue.run_repeating(_job_ciclo, interval=config.intervalo_minutos * 60, first=30)
        log.info("Ciclo automático a cada %d min", config.intervalo_minutos)
    else:
        log.info("Ciclo automático desligado (sem fonte ativa ou sem CHAT_ID)")

    log.info("Bot rodando — fale com ele no privado do Telegram")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

