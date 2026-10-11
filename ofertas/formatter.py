from html import escape
import re

from .models import Oferta

_PLATAFORMA = {
    "mercadolivre": "💛 Mercado Livre",
    "shopee": "🧡 Shopee",
    "amazon": "📦 Amazon",
    "aliexpress": "❤️ AliExpress",
    "magalu": "💙 Magazine Luiza",
}

_TAG_PLATAFORMA = {
    "mercadolivre": "MercadoLivre",
    "shopee": "Shopee",
    "amazon": "Amazon",
    "aliexpress": "AliExpress",
    "magalu": "Magalu",
}


def preco_br(valor: float) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def _limpar_tag(texto: str) -> str:
    # Remove acentos/caracteres especiais para criar hashtag válida
    limpo = re.sub(r"[^\w]", "", texto)
    return limpo.capitalize() if limpo else ""


def montar_caption(o: Oferta) -> str:
    linhas = []

    # Alerta de Super Desconto (>= 60% ou marcado como super desconto)
    if o.is_super_desconto:
        linhas.append("🚨 <b>SUPER OFERTA / POSSÍVEL BUG DE PREÇO</b> 🚨\n")

    linhas.append(f"🔥 <b>{escape(o.titulo[:180])}</b>")
    linhas.append("")

    if o.preco and o.preco_original and o.preco_original > o.preco:
        linhas.append(f"❌ De: <s>{preco_br(o.preco_original)}</s>")
        selo = f"  🔻 <b>-{o.desconto}%</b>" if o.desconto else ""
        linhas.append(f"✅ Por: <b>{preco_br(o.preco)}</b>{selo}")
    elif o.preco:
        selo = f"  🔻 <b>-{o.desconto}%</b>" if o.desconto else ""
        linhas.append(f"✅ <b>{preco_br(o.preco)}</b>{selo}")

    # Cupom com cópia em 1 toque
    if o.cupom:
        linhas.append(f"🎟️ Cupom: <code>{escape(o.cupom.strip().upper())}</code> <i>(toque para copiar)</i>")

    if o.extra:
        linhas.append(escape(o.extra))

    # Plataforma
    plat_nome = _PLATAFORMA.get(o.plataforma, o.plataforma.capitalize())
    linhas += ["", plat_nome]

    # Hashtags dinâmicas
    tags = ["#Ofertas"]
    if o.plataforma in _TAG_PLATAFORMA:
        tags.append(f"#{_TAG_PLATAFORMA[o.plataforma]}")
    if o.categoria:
        cat_tag = _limpar_tag(o.categoria)
        if cat_tag:
            tags.append(f"#{cat_tag}")
    if o.is_super_desconto:
        tags.append("#SuperDesconto")

    linhas.append(" ".join(tags))

    return "\n".join(linhas)

