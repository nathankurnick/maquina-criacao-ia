# Checklist de configuração na plataforma

Os menus mudam de nome com o tempo — se não achar, procure na central de ajuda da plataforma
pelo termo entre aspas. Quem configura é o aluno; você explica e confere.

## Em qualquer plataforma
1. Produto principal criado, com preço e a área de membros com os entregáveis (Sistema 03).
2. Página de vendas (Sistema 02) com o link de checkout do produto principal.
3. **4 order bumps** ligados ao produto principal (4 produtos separados), com a copy de cada um do `order-bump.md`.
4. **Upsell** ("upsell", "one click", "funil de vendas"): produto do upsell criado; a página de
   upsell (link da Netlify do `funil_oto.py`) configurada como página depois da compra; o botão
   de compra em 1 clique da plataforma (se existir) colado em `botao_html` do `oto.json` (se o botão
   aparece dentro do player, use `botao_no_player: true`).
5. **Downsell**: mesma coisa, como destino do "não, obrigado" do upsell.
6. **Página de obrigado**: depois do último passo, mande pra área de membros.
7. **Pixel da Meta** no checkout e na página de vendas (a página de upsell não tem pixel);
   evento de compra (Purchase) configurado na plataforma.
8. **Recuperação**: automação de carrinho abandonado e boleto/PIX (e-mail/WhatsApp) com as
   mensagens do `mensagens.md`.
9. Teste o funil inteiro com uma compra real de valor baixo (ou modo de teste, se houver) e peça
   reembolso depois.

## Kiwify / Hotmart / Payt / Eduzz
Todas têm order bump (use os 4) e upsell pós-compra; os nomes exatos mudam. Termos pra buscar na ajuda:
"order bump", "upsell de 1 clique", "funil", "página de obrigado", "pixel", "recuperação de carrinho".
Na Payt, busque na ajuda: "order bump", "upsell", "one click upsell", "página de obrigado", "pixel do Facebook".

- Bumps e upsell são produtos SEPARADOS na plataforma (não entram no produto principal).
- A página OTO (Netlify) NÃO tem pixel da Meta: o evento Purchase vem da plataforma.
- Se o widget de 1 clique da plataforma tiver um link próprio de recusa, deixe o `recusar_url`
  apontando para o mesmo destino e não esconda nada.
