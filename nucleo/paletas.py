"""Paletas da Máquina (fonte única). O Sistema 02 tem uma cópia; tests/test_paletas.py garante que batem."""

PALETAS = {
    "azul-laranja": {"fundo": "#0a1628", "fundo-claro": "#eef3fb", "fundo-medio": "#0f3460",
                     "destaque": "#f59e0b", "cta": "#f59e0b", "cta-texto": "#0a1628",
                     "texto-claro": "#ffffff", "texto-escuro": "#0a1628"},
    "preto-dourado": {"fundo": "#0c0c0c", "fundo-claro": "#f6f3ec", "fundo-medio": "#1c1a16",
                      "destaque": "#d4af37", "cta": "#d4af37", "cta-texto": "#0c0c0c",
                      "texto-claro": "#ffffff", "texto-escuro": "#0c0c0c"},
    "verde-branco": {"fundo": "#06281c", "fundo-claro": "#eef8f2", "fundo-medio": "#0c4230",
                     "destaque": "#22c55e", "cta": "#22c55e", "cta-texto": "#052e1b",
                     "texto-claro": "#ffffff", "texto-escuro": "#06281c"},
    "vermelho-preto": {"fundo": "#120a0a", "fundo-claro": "#f8f0ef", "fundo-medio": "#2a1111",
                       "destaque": "#ef4444", "cta": "#ef4444", "cta-texto": "#ffffff",
                       "texto-claro": "#ffffff", "texto-escuro": "#120a0a"},
    "grafite-ciano": {"fundo": "#101820", "fundo-claro": "#eef4f7", "fundo-medio": "#1c2b36",
                      "destaque": "#06b6d4", "cta": "#06b6d4", "cta-texto": "#04222b",
                      "texto-claro": "#ffffff", "texto-escuro": "#101820"},
}
PALETA_PADRAO = "azul-laranja"
PALETAS_ROTULO = {
    "azul-laranja": "Azul e laranja", "preto-dourado": "Preto e dourado",
    "verde-branco": "Verde e branco", "vermelho-preto": "Vermelho e preto",
    "grafite-ciano": "Grafite e ciano",
}


def paleta(nome: str) -> dict:
    return PALETAS.get(nome, PALETAS[PALETA_PADRAO])
