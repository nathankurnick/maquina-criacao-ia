# tests/test_entregavel_md.py
from entregavel_md import converter, dividir_slides


def test_titulos_com_id_e_lista_do_sumario():
    html, titulos = converter("# Começo\n\ntexto\n\n## Parte A\n\n## Parte A\n\n### Sub")
    assert '<h1 id="comeco">Começo</h1>' in html
    assert '<h2 id="parte-a">Parte A</h2>' in html and '<h2 id="parte-a-2">Parte A</h2>' in html
    assert "<h3" in html
    assert titulos == [{"nivel": 1, "texto": "Começo", "id": "comeco"},
                       {"nivel": 2, "texto": "Parte A", "id": "parte-a"},
                       {"nivel": 2, "texto": "Parte A", "id": "parte-a-2"}]


def test_paragrafos_juntam_linhas_e_escapam():
    html, _ = converter("linha um\nlinha <dois>\n\noutro")
    assert "<p>linha um linha &lt;dois&gt;</p>" in html and "<p>outro</p>" in html


def test_inline():
    html, _ = converter("**forte** e *leve* e `x<y` e [site](https://a.com?b=1&c=2) e [ruim](javascript:alert(1))")
    assert "<strong>forte</strong>" in html and "<em>leve</em>" in html
    assert "<code>x&lt;y</code>" in html
    assert '<a href="https://a.com?b=1&amp;c=2">site</a>' in html
    assert 'href="javascript' not in html


def test_listas_e_checklist():
    html, _ = converter("- a\n* b\n\n1. um\n2. dois\n\n- [ ] fazer\n- [x] feito")
    assert "<ul><li>a</li><li>b</li></ul>" in html
    assert "<ol><li>um</li><li>dois</li></ol>" in html
    assert '<ul class="checklist"><li>fazer</li><li class="feito">feito</li></ul>' in html


def test_caixas_de_destaque():
    html, _ = converter("> **Dica:** beba água\n> todo dia\n\n> texto comum")
    assert '<aside class="caixa dica"><p><strong>Dica:</strong> beba água todo dia</p></aside>' in html
    assert '<aside class="caixa"><p>texto comum</p></aside>' in html


def test_tabela_e_hr():
    html, _ = converter("| Dia | Treino |\n|---|---|\n| Seg | A |\n| Ter | B |\n\n---")
    assert "<table><thead><tr><th>Dia</th><th>Treino</th></tr></thead>" in html
    assert "<tr><td>Ter</td><td>B</td></tr>" in html and "<hr>" in html


def test_imagens_seguras():
    html, _ = converter("![Foto](imagens/prato.png)\n\n![x](../segredo.png)\n\n![y](/etc/a.png)\n\n![z](https://c.com/i.png)")
    assert '<figure><img src="imagens/prato.png" alt="Foto"></figure>' in html
    assert "segredo" not in html and "/etc" not in html
    assert 'src="https://c.com/i.png"' in html


def test_dividir_slides():
    assert dividir_slides("# A\ntexto\n---\n# B\n\n---\n") == ["# A\ntexto", "# B"]


def test_texto_vazio():
    assert converter("") == ("", [])


def test_imagens_locais_rejeitam_evasoes():
    for src in ["a%2e%2e/b.png", "imagens\\..\\..\\b.png", "a\\..\\b.png", "C:/x.png"]:
        html, _ = converter(f"![x]({src})")
        assert "<img" not in html, src


def test_nul_nao_quebra():
    html, _ = converter("a\x000\x00b")
    assert "\x00" not in html and "<p>" in html


def test_link_com_parenteses_balanceados():
    html, _ = converter("[a](https://x.com/a_(b))")
    assert '<a href="https://x.com/a_(b)">a</a>' in html


def test_href_sem_escape_duplo():
    html, _ = converter("[a](https://x.com?b=1&amp;c=2) [d](https://x.com?b=1&c=2)")
    assert html.count('href="https://x.com?b=1&amp;c=2"') == 2
    assert "&amp;amp;" not in html


def test_lista_com_linha_em_branco_continua():
    html, _ = converter("- a\n\n- b\n\n1. um\n\n2. dois")
    assert "<ul><li>a</li><li>b</li></ul>" in html
    assert "<ol><li>um</li><li>dois</li></ol>" in html


def test_lista_continuacao_e_aninhada():
    html, _ = converter("- a\n  continua\n- b\n  - b1\n  - b2\n- c")
    assert "<li>a continua</li>" in html
    assert "<li>b<ul><li>b1</li><li>b2</li></ul></li>" in html
    assert html.count("<ul>") == 2 and "<li>c</li>" in html


def test_titulo_do_sumario_em_texto_puro():
    html, titulos = converter("# **Forte** e [link](https://a.com) `x`")
    assert titulos == [{"nivel": 1, "texto": "Forte e link x", "id": "forte-e-link-x"}]
    assert '<h1 id="forte-e-link-x"><strong>Forte</strong>' in html


def test_negrito_com_italico():
    html, _ = converter("**a *b* c**")
    assert "<strong>a <em>b</em> c</strong>" in html
