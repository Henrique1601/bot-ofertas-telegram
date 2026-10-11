import asyncio
import logging
import re

from telegram import Bot

from . import ai, db, whatsapp
from .config import config, dentro_do_horario
from .models import Oferta
from .sources import aliexpress, amazon, magalu, mercadolivre, shopee
from .telegram_poster import postar_oferta


log = logging.getLogger("ofertas.pipeline")


def coletar() -> list[Oferta]:
    """Busca ofertas nas fontes automáticas ativas (sem link de afiliado ainda, no caso do ML)."""
    todas: list[Oferta] = []

    if config.fonte_shopee.get("ativa"):
        if config.shopee_app_id and config.shopee_app_secret:
            try:
                todas += shopee.buscar_ofertas(int(config.fonte_shopee.get("limite", 30)))
            except Exception as e:
                log.error("Shopee: %s", e)
        else:
            log.warning("Shopee ativa no config.yaml mas sem credenciais no .env — pulando")

    if config.fonte_amazon.get("ativa"):
        if config.amazon_tag:
            try:
                todas += amazon.buscar_ofertas()
            except Exception as e:
                log.error("Amazon: %s", e)
        else:
            log.warning("Amazon ativa no config.yaml mas sem AMAZON_TAG no .env — pulando")

    if config.fonte_ml.get("ativa"):
        if mercadolivre.tem_sessao():
            try:
                todas += mercadolivre.buscar_ofertas()
            except Exception as e:
                log.error("Mercado Livre: %s", e)
        else:
            log.warning("Mercado Livre ativo mas sem sessão de afiliado — coloque cookies.json em data/ ou rode: uv run python -m ofertas ml-login")

    if config.fonte_aliexpress.get("ativa"):
        try:
            todas += aliexpress.buscar_ofertas()
        except Exception as e:
            log.error("AliExpress: %s", e)

    if config.fonte_magalu.get("ativa"):
        try:
            todas += magalu.buscar_ofertas()
        except Exception as e:
            log.error("Magazine Luiza: %s", e)

    return todas


def filtrar(ofertas: list[Oferta]) -> list[Oferta]:
    aprovadas = []
    for o in ofertas:
        if not o.titulo:
            continue
        if db.ja_postada(o.uid, config.nao_repetir_dias):
            continue
        if config.desconto_minimo and (o.desconto or 0) < config.desconto_minimo:
            continue
        if o.preco is not None:
            if config.preco_minimo and o.preco < config.preco_minimo:
                continue
            if config.preco_maximo and o.preco > config.preco_maximo:
                continue
        titulo = o.titulo.lower()
        if any(p in titulo for p in config.palavras_bloqueadas):
            continue
        aprovadas.append(o)
    return aprovadas


def _chave_similar(titulo: str) -> str:
    """Variações do mesmo produto (cor, tamanho) costumam repetir as primeiras palavras."""
    return " ".join(re.findall(r"\w+", titulo.lower())[:5])


def escolher(ofertas: list[Oferta], n: int) -> list[Oferta]:
    """Top N por desconto, alternando plataformas e pulando variações do mesmo produto."""
    filas: dict[str, list[Oferta]] = {}
    for o in sorted(ofertas, key=lambda o: o.desconto or 0, reverse=True):
        filas.setdefault(o.plataforma, []).append(o)
    ordem = sorted(filas.values(), key=lambda f: f[0].desconto or 0, reverse=True)
    escolhidas: list[Oferta] = []
    vistas: set[str] = set()
    while len(escolhidas) < n and any(ordem):
        for fila in ordem:
            while fila:
                o = fila.pop(0)
                chave = _chave_similar(o.titulo)
                if chave not in vistas:
                    vistas.add(chave)
                    escolhidas.append(o)
                    break
            if len(escolhidas) >= n:
                break
    return escolhidas


async def avisar_dono(bot: Bot, texto: str) -> None:
    """Manda um aviso no privado do dono (se configurado) — para operação sem supervisão."""
    if not config.owner_id:
        return
    try:
        await bot.send_message(config.owner_id, texto)
    except Exception as e:
        log.warning("Não consegui avisar o dono: %s", e)


async def executar_ciclo(bot: Bot) -> int:
    """Um ciclo completo: coletar -> filtrar -> escolher -> gerar links -> postar. Retorna nº de posts."""
    if not dentro_do_horario():
        log.info("Fora do horário ativo (%s) — ciclo pulado", config.horario_ativo)
        return 0

    brutas = await asyncio.to_thread(coletar)
    boas = filtrar(brutas)
    escolhidas = escolher(boas, config.max_posts_por_ciclo)

    # Mercado Livre: gerar link de afiliado só das escolhidas (linkbuilder é caro)
    ml_pendentes = [o for o in escolhidas if o.plataforma == "mercadolivre" and not o.url_afiliado]
    if ml_pendentes:
        try:
            await asyncio.to_thread(mercadolivre.gerar_links_afiliado, ml_pendentes)
        except Exception as e:
            log.error("Linkbuilder ML falhou: %s", e)
            if "Sessão" in str(e):
                await avisar_dono(bot, f"⚠️ Mercado Livre parou de gerar links: {e}")

    # Fallback: Se algum produto ficou sem link de afiliado, preenche a cota com outras ofertas aprovadas (Shopee, etc.)
    validas = [o for o in escolhidas if o.url_afiliado]
    if len(validas) < config.max_posts_por_ciclo:
        outras = [o for o in boas if o not in escolhidas and o.url_afiliado]
        for extra in outras:
            validas.append(extra)
            if len(validas) >= config.max_posts_por_ciclo:
                break

    postadas = 0
    canais_destino = [config.chat_id] + [c for c in config.canais_extras if c != config.chat_id]

    for o in validas:
        if not o.url_afiliado:
            log.warning("Sem link de afiliado, pulando: %s", o.titulo[:60])
            continue

        # 1. Menor preço histórico
        if o.preco:
            o.is_menor_preco = db.verificar_menor_preco(o.uid, o.preco)

        # 2. Enriquecimento por IA (Google Gemini) se chave configurada
        if config.gemini_api_key:
            try:
                novo_tit, destaques = await asyncio.to_thread(ai.enriquecer_oferta, o.titulo, o.extra)
                if novo_tit:
                    o.titulo = novo_tit
                o.destaques_ia = destaques
            except Exception as e_ai:
                log.warning("Falha ao enriquecer oferta com IA: %s", e_ai)

        # 3. Radar de Desejos (Notificar inscritos interessados)
        try:
            desejos = db.buscar_desejos_compativeis(o)
            for d in desejos:
                try:
                    texto_desejo = (
                        f"🔔 <b>RADAR DE OFERTAS: SEU DESEJO APARECEU!</b>\n\n"
                        f"Você cadastrou um alerta para: <b>{d['termo']}</b>\n\n"
                        f"🔥 <b>{o.titulo}</b>\n"
                        f"✅ Preço: <b>R$ {o.preco:.2f}</b>\n\n"
                        f"🛒 <a href=\"{o.url_afiliado}\">Clique aqui para ver a oferta</a>"
                    )
                    await bot.send_message(d["user_id"], texto_desejo, parse_mode="HTML")
                except Exception as e_d:
                    log.warning("Falha ao notificar desejo para user %s: %s", d.get("user_id"), e_d)
        except Exception as e_w:
            log.warning("Erro ao verificar radar de desejos: %s", e_w)

        # 4. Postagem no Telegram (Canal Principal e Canais Extras)
        msg_principal = None
        for chat in canais_destino:
            try:
                msg = await postar_oferta(bot, o, chat)
                if chat == config.chat_id:
                    msg_principal = msg
            except Exception as e:
                log.error("Falha ao postar '%s' no canal %s: %s", o.titulo[:60], chat, e)
        
        if msg_principal:
            db.registrar(o, chat_id=config.chat_id, message_id=msg_principal.message_id)
            postadas += 1
        elif canais_destino:
            db.registrar(o, chat_id=config.chat_id)
            postadas += 1

        # 5. Cross-Posting no WhatsApp (Canais/Grupos)
        try:
            await asyncio.to_thread(whatsapp.postar_whatsapp, o)
        except Exception as e_wa:
            log.warning("Erro ao postar no WhatsApp: %s", e_wa)

        if o is not validas[-1]:
            await asyncio.sleep(config.espacamento_segundos)

    log.info("Ciclo: %d coletadas, %d aprovadas, %d postadas", len(brutas), len(boas), postadas)
    return postadas


