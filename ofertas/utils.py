import json
import re
from bs4 import BeautifulSoup
import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
)


def sessao() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    })
    return s


def parse_preco_br(texto: str | None) -> float | None:
    """Converte 'R$ 1.234,56' / '1.234' / '56,43' em float."""
    t = re.sub(r"[^\d,.]", "", texto or "")
    if not t:
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") > 1 or (t.count(".") == 1 and len(t.rsplit(".", 1)[1]) == 3):
        t = t.replace(".", "")  # ponto de milhar, sem centavos
    try:
        return float(t)
    except ValueError:
        return None


def extrair_urls(texto: str | None) -> list[str]:
    return re.findall(r"https?://\S+", texto or "")


_STOPWORDS_CUPOM = {
    "CUPOM", "DESCONTO", "OFERTA", "PROMOÇÃO", "PROMOCAO", "VALOR", "PRECO", "PREÇO",
    "VALIDO", "VÁLIDO", "FRETE", "GRATIS", "GRÁTIS", "PRIME", "FULL", "PIX", "AQUI",
    "HOJE", "AGORA", "PARA", "COM", "DISPONIVEL", "DISPONÍVEL", "ATIVO", "NOVO", "EXCLUSIVO",
    "HEADER", "FOOTER", "WRAPPER", "CONTAINER", "BUTTON", "SCRIPT", "STYLE", "LINK", "PAGE"
}


def extrair_cupom_texto(texto: str | None) -> str | None:
    """Detecta códigos de cupom em textos (ex: 'Cupom de 10% com CUPOM10' -> 'CUPOM10')."""
    if not texto:
        return None

    # Se for HTML completo, limpa scripts/tags antes de procurar
    if "<html" in texto.lower() or "<div" in texto.lower() or "<body" in texto.lower():
        try:
            soup = BeautifulSoup(texto, "lxml")
            for tag in soup(["script", "style", "noscript", "svg", "path", "head"]):
                tag.decompose()
            texto = soup.get_text(" ", strip=True)
        except Exception:
            texto = re.sub(r"<[^>]+>", " ", texto)

    padroes = [
        r"\b(?:cupom|c[oó]digo|use|voucher)\s*(?:de|com)?\s*[:=]?\s*([A-Za-z0-9_\-]{4,20})\b",
    ]

    for p in padroes:
        for m in re.finditer(p, texto, re.IGNORECASE):
            raw = m.group(1).strip()
            candidato = raw.upper()
            if candidato in _STOPWORDS_CUPOM:
                continue
            if re.match(r"^\d+%$", candidato) or candidato.startswith("R$") or re.match(r"^\d+$", candidato):
                continue
            if any(cand_part in candidato for cand_part in ("FOOTER", "HEADER", "WRAPPER", "HELPER", "CONTAINER")):
                continue
            # Critério: se for só letras minúsculas no texto original e não tiver números, só aceita se estiver explicitamente após ':' ou '=' ou tiver números/maiusculas
            if raw.islower() and not any(ch.isdigit() for ch in raw):
                continue
            return candidato

    return None




def extrair_produto_jsonld(html: str) -> dict | None:
    """Extrai metadados estruturados Schema.org (JSON-LD) e OpenGraph de páginas de e-commerce.

    Garante resiliência total caso o site altere suas classes CSS frontend.
    """
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")

    # 1. Tenta JSON-LD Schema.org
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            dados = json.loads(script.string or "")
            if isinstance(dados, list):
                dados = dados[0]
            if isinstance(dados, dict):
                # Se for @graph, procura o item Product
                if "@graph" in dados and isinstance(dados["@graph"], list):
                    for item in dados["@graph"]:
                        if item.get("@type") == "Product":
                            dados = item
                            break

                if dados.get("@type") in ("Product", "IndividualProduct"):
                    titulo = dados.get("name")
                    imagem = dados.get("image")
                    if isinstance(imagem, list) and imagem:
                        imagem = imagem[0]
                    if isinstance(imagem, dict):
                        imagem = imagem.get("url")

                    preco = None
                    offers = dados.get("offers") or {}
                    if isinstance(offers, list) and offers:
                        offers = offers[0]
                    if isinstance(offers, dict):
                        preco = float(offers.get("price") or offers.get("lowPrice") or 0) or None

                    return {
                        "titulo": str(titulo).strip() if titulo else None,
                        "preco": preco,
                        "imagem": str(imagem).strip() if imagem else None,
                    }
        except (json.JSONDecodeError, TypeError, ValueError):
            continue

    # 2. Fallback: Metatags OpenGraph e Microdata
    og_title = soup.select_one('meta[property="og:title"], meta[name="twitter:title"]')
    og_image = soup.select_one('meta[property="og:image"], meta[name="twitter:image"]')
    meta_price = soup.select_one('meta[property="product:price:amount"], meta[itemprop="price"]')

    titulo = og_title.get("content") if og_title else None
    imagem = og_image.get("content") if og_image else None
    preco = float(meta_price.get("content", 0)) if meta_price and meta_price.get("content") else None

    if titulo or preco or imagem:
        return {
            "titulo": str(titulo).strip() if titulo else None,
            "preco": preco,
            "imagem": str(imagem).strip() if imagem else None,
        }

    return None
