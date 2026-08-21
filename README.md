# Carlos Reels Automation

Automação do Instagram para o perfil-piloto: alterna uma fila de vídeos, troca a frase na tela e a legenda e publica um Reel por hora.

## Modo de teste
- Publica como **Trial Reel / Reel de Teste** por padrão.
- O conteúdo vai primeiro para não seguidores.
- A graduação para o público normal fica manual enquanto avaliamos os resultados.

## Estrutura
- Vídeos: Google Drive `Carlos Reels Automation / 01 - Videos`.
- Frases/legendas: `content.json` (40 combinações iniciais).
- Frequência: uma execução por hora, 24h/dia durante o teste.
- Estado: `state.json` evita repetir o mesmo vídeo antes de completar a volta.
- Segurança: o token do Instagram fica apenas em GitHub Actions Secrets.

## Para ativar
1. Compartilhe a pasta `01 - Videos` no Google Drive como **Qualquer pessoa com o link > Leitor**.
2. Coloque os vídeos selecionados nessa pasta.
3. No GitHub, crie o secret `INSTAGRAM_ACCESS_TOKEN` e cole o token novo gerado pela Meta.
4. O workflow está programado para rodar de hora em hora; também pode ser acionado manualmente para o primeiro teste.

A automação não publica enquanto o token ou os vídeos estiverem ausentes.
