"""AliExpress: conversão de links e busca de ofertas.

Suporta links diretos (pt.aliexpress.com/item/123.html) e links encurtados (a.aliexpress.com/xxx).
Extração resiliente via JSON-LD/OpenGraph + gerador de link com tracking ID.
"""
import logging
import re
from bs4 import BeautifulSoup

from ..config import config
from ..models import Oferta
from ..utils import extrair_cupom_texto, extrair_produto_jsonld, parse_preco_br, sessao

log = logging.getLogger("ofertas.aliexpress")

_RE_ITEM = re.compile(r"/item/(\d+)\.html")
_RE_ITEM_ID = re.compile(r"(\d{10,20})")


def e_link(url: str) -> bool:
    return any(d in url for d in ("aliexpress.com", "aliexpress.ru", "a.aliexpress.com", "s.click.aliexpress.com"))


def _expandir_link(url: str) -> str:
    """Expande links curtos como a.aliexpress.com ou s.click.aliexpress.com."""
    if "a.aliexpress.com" in url or "s.click.aliexpress.com" in url:
        try:
            r = sessao().get(url, allow_redirects=True, timeout=20)
            return r.url
        except Exception as e:
            log.warning("Falha ao expandir link do AliExpress %s: %s", url, e)
    return url


def _extrair_id(url: str) -> str:
    m = _RE_ITEM.search(url)
    if m:
        return m.group(1)
    m = _RE_ITEM_ID.search(url)
    if m:
        return m.group(1)
    return url.split("?")[0].rstrip("/").rsplit("/", 1)[-1][:30]


def _gerar_url_afiliado(url_limpa: str, id_produto: str) -> str:
    tracking_id = getattr(config, "aliexpress_tracking_id", "") or ""
    if not tracking_id:
        return url_limpa
    sep = "&" if "?" in url_limpa else "?"
    return f"{url_limpa}{sep}aff_platform=true&sk={tracking_id}&aff_trace_key={tracking_id}"


def _detalhes(url: str) -> tuple[str | None, float | None, float | None, str | None, str | None]:
    """Retorna (titulo, preco, preco_original, imagem, cupom)."""
    s = sessao()
    try:
        r = s.get(url, timeout=25)
        html = r.text

        # 1. Tentar JSON-LD e OpenGraph primeiro (resiliente a mudanças de layout)
        ld = extrair_produto_jsonld(html)
        titulo = ld.get("titulo") if ld else None
        preco = ld.get("preco") if ld else None
        imagem = ld.get("imagem") if ld else None
        preco_original = None

        # 2. Refinamento via BeautifulSoup caso falte algo
        soup = BeautifulSoup(html, "lxml")
        if not titulo:
            el = soup.select_one("h1[data-pl='product-title'], .product-title-text, .title--title--1lK9qC5, h1")
            if el:
                titulo = el.get_text(strip=True)

        if not preco:
            el = soup.select_one(".price--currentPriceText--2_2_x, .product-price-current, .notranslate.pdp-product-price")
            if el:
                preco = parse_preco_br(el.get_text())

        el_orig = soup.select_one(".price--originalText--3fXGZ0W, .product-price-original, .pdp-product-price-original")
        if el_orig:
            preco_original = parse_preco_br(el_orig.get_text())

        if not imagem:
            el_img = soup.select_one(".magnifier--image--xJqW4xW, img.pdp-magnifier-image, meta[property='og:image']")
            if el_img:
                imagem = el_img.get("content") or el_img.get("src")

        cupom = extrair_cupom_texto(html)
        return titulo, preco, preco_original, imagem, cupom
    except Exception as e:
        log.warning("Falha ao raspar produto AliExpress (%s): %s", url, e)
        return None, None, None, None, None


def converter(url: str) -> Oferta:
    """Converte URL do AliExpress em Oferta com dados e link afiliado."""
    url_real = _expandir_link(url)
    id_produto = _extrair_id(url_real)
    url_limpa = f"https://pt.aliexpress.com/item/{id_produto}.html" if id_produto.isdigit() else url_real.split("?")[0]

    titulo, preco, preco_original, imagem, cupom = _detalhes(url_limpa)
    url_afiliado = _gerar_url_afiliado(url_limpa, id_produto)

    return Oferta(
        plataforma="aliexpress",
        id_produto=id_produto,
        titulo=titulo or f"Oferta AliExpress ({id_produto})",
        url_afiliado=url_afiliado,
        url_produto=url_limpa,
        preco=preco,
        preco_original=preco_original,
        imagem=imagem,
        cupom=cupom,
    )


def buscar_ofertas() -> list[Oferta]:
    """Busca ofertas automáticas no AliExpress (se configurado)."""
    # Se buscas automáticas forem ativadas no config.yaml:
    buscas = config.fonte_aliexpress.get("buscas") or []
    if not buscas:
        return []
    s = sessao()
    ofertas: list[Oferta] = []
    for termo in buscas:
        try:
            url = "https://pt.aliexpress.com/w/wholesale-" + termo.replace(" ", "-") + ".html"
            r = s.get(url, timeout=25)
            soup = BeautifulSoup(r.text, "lxml")
            cards = soup.select("div[class*='search-item'], div[class*='list--galleryItem']")
            for card in cards[:10]:
                a = card.select_one("a[href*='/item/']")
                if not a or not a.get("href"):
                    continue
                href = a["href"]
                if href.startswith("//"):
                    href = "https:" + href
                id_prod = _extrair_id(href)
                url_limpa = f"https://pt.aliexpress.com/item/{id_prod}.html"
                preco_el = card.select_one("[class*='price--currentPrice'], [class*='current--price']")
                preco = parse_preco_br(preco_el.get_text()) if preco_el else None
                tit_el = card.select_one("[class*='title--title'], h1, h3")
                tit = tit_el.get_text(strip=True) if tit_el else f"Produto AliExpress {id_prod}"
                img_el = card.select_one("img")
                img = (img_el.get("src") or img_el.get("data-src")) if img_el else None
                if img and img.startswith("//"):
                    img = "https:" + img

                ofertas.append(Oferta(
                    plataforma="aliexpress",
                    id_produto=id_prod,
                    titulo=tit,
                    url_afiliado=_gerar_url_afiliado(url_limpa, id_prod),
                    url_produto=url_limpa,
                    preco=preco,
                    imagem=img,
                ))
        except Exception as e:
            log.error("AliExpress busca '%s': %s", termo, e)
    return ofertas
