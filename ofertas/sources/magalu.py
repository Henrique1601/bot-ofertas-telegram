"""Magazine Luiza / Magazine Você: conversão de links e busca de ofertas.

Reescreve links de produtos do Magazine Luiza para a loja do afiliado no Magazine Você:
https://www.magazineluiza.com.br/.../p/{id}/ -> https://www.magazinevoce.com.br/{MAGALU_LOJA}/p/{id}/
"""
import logging
import re
from bs4 import BeautifulSoup

from ..config import config
from ..models import Oferta
from ..utils import extrair_cupom_texto, extrair_produto_jsonld, parse_preco_br, sessao

log = logging.getLogger("ofertas.magalu")

_RE_MAGALU_P = re.compile(r"/p/([a-zA-Z0-9]+)")
_RE_SKU = re.compile(r"([0-9a-zA-Z]{7,12})")


def e_link(url: str) -> bool:
    return any(d in url for d in ("magazineluiza.com.br", "magazinevoce.com.br", "magalu.com"))


def _extrair_id(url: str) -> str:
    m = _RE_MAGALU_P.search(url)
    if m:
        return m.group(1)
    m = _RE_SKU.search(url)
    if m:
        return m.group(1)
    return url.split("?")[0].rstrip("/").rsplit("/", 1)[-1][:30]


def _gerar_url_afiliado(url: str, id_produto: str) -> str:
    loja = getattr(config, "magalu_loja", "") or ""
    if not loja:
        return url.split("?")[0]
    
    # Se a URL tiver o padrão /p/{id}/ ou /{categoria}/p/{id}/
    m = _RE_MAGALU_P.search(url)
    if m:
        # Ex: https://www.magazinevoce.com.br/minhaloja/p/2345678/
        return f"https://www.magazinevoce.com.br/{loja}/p/{m.group(1)}/"
    
    # Fallback para caminho limpo
    path = url.split("magazineluiza.com.br", 1)[-1].split("magazinevoce.com.br", 1)[-1].split("?")[0].lstrip("/")
    # Se já começar com o nome de uma loja, remove
    partes = path.split("/")
    if partes and partes[0] not in ("p", "selecao"):
        path = "/".join(partes[1:]) if len(partes) > 1 else path
    return f"https://www.magazinevoce.com.br/{loja}/{path}"


def _detalhes(url: str) -> tuple[str | None, float | None, float | None, str | None, str | None]:
    s = sessao()
    try:
        r = s.get(url, timeout=25)
        html = r.text

        # 1. JSON-LD e OpenGraph (resiliente)
        ld = extrair_produto_jsonld(html)
        titulo = ld.get("titulo") if ld else None
        preco = ld.get("preco") if ld else None
        imagem = ld.get("imagem") if ld else None
        preco_original = None

        # 2. BeautifulSoup fallback
        soup = BeautifulSoup(html, "lxml")
        if not titulo:
            el = soup.select_one("h1[data-testid='heading-product-title'], h1")
            if el:
                titulo = el.get_text(strip=True)

        if not preco:
            el = soup.select_one("[data-testid='price-value'], .price-template__text, .price-value")
            if el:
                preco = parse_preco_br(el.get_text())

        el_orig = soup.select_one("[data-testid='price-original'], .price-template__from")
        if el_orig:
            preco_original = parse_preco_br(el_orig.get_text())

        if not imagem:
            el_img = soup.select_one("img[data-testid='image-selected-thumbnail'], meta[property='og:image']")
            if el_img:
                imagem = el_img.get("content") or el_img.get("src")

        cupom = extrair_cupom_texto(html)
        return titulo, preco, preco_original, imagem, cupom
    except Exception as e:
        log.warning("Falha ao raspar produto Magalu (%s): %s", url, e)
        return None, None, None, None, None


def converter(url: str) -> Oferta:
    """Converte URL da Magalu em Oferta com dados e link do Magazine Você."""
    id_produto = _extrair_id(url)
    titulo, preco, preco_original, imagem, cupom = _detalhes(url)
    url_afiliado = _gerar_url_afiliado(url, id_produto)

    return Oferta(
        plataforma="magalu",
        id_produto=id_produto,
        titulo=titulo or f"Oferta Magazine Luiza ({id_produto})",
        url_afiliado=url_afiliado,
        url_produto=url.split("?")[0],
        preco=preco,
        preco_original=preco_original,
        imagem=imagem,
        cupom=cupom,
    )


def buscar_ofertas() -> list[Oferta]:
    """Busca ofertas do dia no Magazine Luiza se ativado no config."""
    if not config.fonte_magalu.get("ativa"):
        return []
    s = sessao()
    ofertas: list[Oferta] = []
    url = "https://www.magazineluiza.com.br/selecao/ofertas-do-dia/"
    try:
        r = s.get(url, timeout=25)
        soup = BeautifulSoup(r.text, "lxml")
        cards = soup.select("li[data-testid='product-card-container'], a[data-testid='product-card-container']")
        for card in cards[:15]:
            a = card if card.name == "a" else card.select_one("a[data-testid='product-card-container'], a")
            if not a or not a.get("href"):
                continue
            href = a["href"]
            if not href.startswith("http"):
                href = "https://www.magazineluiza.com.br" + href
            id_prod = _extrair_id(href)
            
            tit_el = card.select_one("[data-testid='product-title'], h2, h3")
            tit = tit_el.get_text(strip=True) if tit_el else f"Oferta Magalu {id_prod}"
            
            preco_el = card.select_one("[data-testid='price-value']")
            preco = parse_preco_br(preco_el.get_text()) if preco_el else None
            
            preco_orig_el = card.select_one("[data-testid='price-original']")
            preco_orig = parse_preco_br(preco_orig_el.get_text()) if preco_orig_el else None
            
            img_el = card.select_one("img")
            img = (img_el.get("src") or img_el.get("data-src")) if img_el else None

            ofertas.append(Oferta(
                plataforma="magalu",
                id_produto=id_prod,
                titulo=tit,
                url_afiliado=_gerar_url_afiliado(href, id_prod),
                url_produto=href.split("?")[0],
                preco=preco,
                preco_original=preco_orig,
                imagem=img,
            ))
        log.info("Magalu: %d ofertas coletadas", len(ofertas))
    except Exception as e:
        log.error("Magalu busca ofertas: %s", e)
    return ofertas
