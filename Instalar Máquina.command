#!/bin/bash
# Dois cliques neste arquivo instalam (ou atualizam) a Máquina Criação IA.
AQUI="$(cd "$(dirname "$0")" && pwd)"
cd "$AQUI" || exit 1
bash "$AQUI/instalar.sh"
STATUS=$?
echo
if [ $STATUS -eq 0 ]; then
  echo "Pode fechar esta janela."
else
  echo "A instalação não terminou. Leia a mensagem acima e, se precisar, mande um print pro suporte."
fi
read -r -p "Aperte Enter pra fechar..." _
exit $STATUS
