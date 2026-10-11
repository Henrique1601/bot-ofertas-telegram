from dataclasses import dataclass


@dataclass
class Oferta:
    plataforma: str            # "mercadolivre" | "shopee" | "amazon" | "aliexpress" | "magalu"
    id_produto: str
    titulo: str
    url_afiliado: str          # vazio até o link de afiliado ser gerado
    url_produto: str = ""
    preco: float | None = None
    preco_original: float | None = None
    desconto_pct: int | None = None
    imagem: str | None = None
    extra: str | None = None   # avaliação, frete grátis, "no Pix" etc.
    cupom: str | None = None   # código do cupom para cópia com 1 clique
    categoria: str | None = None # para hashtags automáticas
    is_menor_preco: bool = False # selo de menor preço histórico (últimos 30/60 dias)
    destaques_ia: list[str] | None = None # 2-3 bullets técnicos resumidos pela IA


    @property
    def uid(self) -> str:
        return f"{self.plataforma}:{self.id_produto}"

    @property
    def desconto(self) -> int | None:
        if self.desconto_pct:
            return self.desconto_pct
        if self.preco and self.preco_original and self.preco_original > self.preco:
            return round(100 * (1 - self.preco / self.preco_original))
        return None

    @property
    def is_super_desconto(self) -> bool:
        return (self.desconto or 0) >= 60
