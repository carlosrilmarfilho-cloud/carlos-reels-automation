# Carlos Reels Automation

Automação do Instagram para o perfil-piloto: alterna uma fila de vídeos, troca a frase na tela e a legenda e publica um Reel por hora.

## Estrutura
- Vídeos: Google Drive `Carlos Reels Automation / 01 - Videos`.
- Frases/legendas: `content.json` (40 combinações iniciais).
- Frequência: uma execução por hora, 24h/dia durante o teste.
- Estado: `state.json` evita repetir o mesmo vídeo antes de completar a volta.
- Segurança: o token do Instagram fica apenas em GitHub Actions Secrets.

## Para ativar
1. Compartilhe a pasta `01 - Videos` no Google Drive como **Qualquer pessoa com o link > Leitor**.
2. Coloque os vídeos nessa pasta.
3. No GitHub, crie o secret `INSTAGRAM_ACCESS_TOKEN` e cole o token novo que você gerou na Meta.
4. Rode o workflow manualmente uma vez em Actions para validar. Depois ele continua sozinho de hora em hora.

A automação não inicia publicação enquanto o token ou os vídeos estiverem ausentes.
