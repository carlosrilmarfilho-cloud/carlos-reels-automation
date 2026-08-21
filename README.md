# Carlos Reels Automation

Automação para escolher um vídeo, trocar a frase na tela, trocar a legenda e publicar um Reel por hora via API oficial do Instagram.

## Fluxo

- Busca os vídeos de uma pasta compartilhada do Google Drive (ou usa a pasta `videos/` do repositório).
- Alterna os vídeos em ordem, sem repetir até completar a volta.
- Alterna as frases e legendas de `content.json`.
- Renderiza em 1080x1920 com H.264 + AAC e texto na tela.
- Hospeda somente o vídeo já renderizado em um branch temporário `media-host`.
- Publica via API oficial do Instagram e só então avança o contador.
- Executa uma vez por hora.

## Configuração final

1. No GitHub, crie o secret `INSTAGRAM_ACCESS_TOKEN` com um token NOVO da Meta. Nunca salve o token no código ou no chat.
2. Se usar Google Drive, crie a variável `GDRIVE_FOLDER_URL` com o link da pasta compartilhada que contém os vídeos.
3. Deixe o repositório público, pois a Meta precisa acessar temporariamente `latest.mp4` para publicar o Reel.
4. Em **Settings > Actions > General > Workflow permissions**, habilite `Read and write permissions`.
5. Troque frases/legendas em `content.json`.
6. Rode manualmente `Postar Reel a cada hora` uma vez para o teste inicial.

O cron `7 * * * *` executa uma vez por hora. GitHub Actions pode atrasar alguns minutos em horários de pico.
