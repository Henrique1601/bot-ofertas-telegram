"""Módulo de enriquecimento de ofertas via IA (Google Gemini).

Limpa títulos poluídos de marketplaces e extrai 2 a 3 destaques técnicos reais.
Totalmente opcional: se GEMINI_API_KEY não estiver no .env, não afeta o fluxo normal.
"""
import json
import logging
import os
import requests

from .config import config

log = logging.getLogger("ofertas.ai")


def enriquecer_oferta(titulo: str, extra: str | None = None) -> tuple[str, list[str] | None]:
    """Retorna (titulo_limpo, destaques). Se não houver chave ou falhar, retorna o original."""
    chave = getattr(config, "gemini_api_key", "") or os.getenv("GEMINI_API_KEY", "").strip()
    if not chave:
        return titulo, None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={chave}"
    prompt = (
        "Você é um redator especialista em e-commerce. "
        "Limpe o título do produto removendo palavras repetitivas, termos de spam de busca (ex: 'promoção', 'original', 'envio rapido') "
        "e destaque 2 ou 3 pontos fortes técnicos reais.\n\n"
        f"Título original: {titulo}\n"
        f"Informações adicionais: {extra or 'nenhuma'}\n\n"
        "Responda EXCLUSIVAMENTE em formato JSON com o seguinte schema:\n"
        "{\n"
        '  "titulo_limpo": "Título conciso e profissional com marca e modelo (máx 80 caracteres)",\n'
        '  "destaques": ["Destaque 1", "Destaque 2", "Destaque 3"]\n'
        "}"
    )

    try:
        corpo = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
        }
        r = requests.post(url, json=corpo, timeout=8)
        if r.status_code != 200:
            log.warning("Gemini API retornou HTTP %s: %s", r.status_code, r.text[:200])
            return titulo, None

        dados = r.json()
        texto_resp = dados["candidates"][0]["content"]["parts"][0]["text"].strip()
        resultado = json.loads(texto_resp)

        titulo_limpo = resultado.get("titulo_limpo") or titulo
        destaques = resultado.get("destaques") or None
        if destaques and isinstance(destaques, list):
            destaques = [str(d).strip() for d in destaques[:3] if str(d).strip()]

        return titulo_limpo, destaques or None
    except Exception as e:
        log.warning("Falha no enriquecimento por IA: %s", e)
        return titulo, None
