# DJ's Best Friend

Ferramenta pessoal em Python (FastAPI) pra buscar musicas e baixar o audio na
melhor qualidade disponivel, com duas fontes:

- **Spotify** (via [spotdl](https://github.com/spotDL/spotify-downloader)): busca
  metadados no Spotify, baixa o audio correspondente no YouTube Music e reencoda
  para mp3 320kbps, com capa/artista/album embutidos.
- **YouTube** (via [yt-dlp](https://github.com/yt-dlp/yt-dlp) direto): baixa o
  melhor stream de audio disponivel **sem reencodar**, preservando o bitrate real
  da fonte.

Feito pra rodar na sua propria maquina, pra uso pessoal — sem contas, sem
pagamento, sem distribuicao pra terceiros.

## Recursos

- Sugestoes "em alta essa semana" na tela inicial
- Busca com preview de audio antes de baixar, pra confirmar que e a musica certa
- Duracao da faixa e **BPM** (batidas por minuto) mostrados ao lado de cada
  resultado
- Painel "tocando agora" com progresso do download em tempo real
- Dashboard simples com total de musicas baixadas, espaco em disco usado e
  quantas foram baixadas nos ultimos 7 dias (le do seu proprio historico local,
  sem servidor nem conta)

### Sobre o calculo de BPM e o preview

O endpoint do Spotify que entrega BPM pronto (`audio-features`) leva 403 com
Client Credentials (app sem usuario logado) — e apps novos tambem quase nunca
recebem `preview_url` (o clipe oficial de 30s) nas buscas. Duas formas de
contornar isso, nessa ordem de prioridade:

1. **Conectar com Spotify** (botao no topo direito): faz login de verdade
   (Authorization Code + PKCE, sem client secret, sem o app ver sua senha).
   Autenticado como usuario real, o `audio-features` costuma funcionar —
   assim o BPM vem oficial da Spotify, instantaneo, pra qualquer resultado.
2. Sem estar conectado: BPM e **calculado localmente**
   ([librosa](https://librosa.org/)) em cima do `preview_url` (quando existe)
   ou de um clipe curto do video equivalente no YouTube (achado automaticamente
   por titulo+artista). Resultados do YouTube (fonte "YouTube" na busca) usam
   esse mesmo caminho.

Precisa cadastrar o Redirect URI usado (`SPOTIFY_REDIRECT_URI`, padrao
`http://127.0.0.1:8000/callback`) no dashboard do app Spotify pra "Conectar com
Spotify" funcionar.

### Sobre as sugestoes "em alta essa semana"

Duas fontes possiveis, nessa ordem de prioridade:

1. **Uma playlist real do Spotify** (ex: a "mint"), configurada via
   `SPOTIFY_TRENDING_PLAYLIST_ID` no `.env` — so funciona com login feito
   (**Conectar com Spotify**), porque a Spotify bloqueia (403/404) esse acesso
   pra Client Credentials (testado com varias playlists, inclusive as
   proprias da Spotify). Puxada ao vivo a cada carregamento, entao acompanha
   as mudancas da playlist de verdade.
2. Se nao estiver configurada, ou se falhar mesmo logado: cai pro grafico
   publico "mais tocadas" da Apple Music (sem chave, sem login — pais/genero
   configuraveis via `TRENDING_STOREFRONT`/`TRENDING_GENRE_ID`), resolvendo
   cada faixa de volta pro Spotify via busca normal pra manter o mesmo
   formato de item usado no resto do site.

## Sobre qualidade de audio

Nenhum desses caminhos baixa do "servidor original" do Spotify — o Spotify não
expõe os arquivos de audio brutos. Tanto o spotdl quanto o modo YouTube direto
buscam o audio no YouTube/YouTube Music, cujo stream de audio normalmente já vem
limitado a algo entre 128-160kbps (opus/AAC). Reencodar para 320kbps não
recupera qualidade que não estava lá — só aumenta o tamanho do arquivo. Por isso
o site oferece as duas opções: "original" pra quem quer o stream cru sem
retrabalho, e "320k mp3" pra quem quer compatibilidade máxima (tocadores antigos,
metadados/capa embutidos) mesmo sabendo que o teto de qualidade é o mesmo.

## Requisitos

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html) instalado e no PATH (usado pelo
  spotdl, pelo yt-dlp e pelo librosa pra ler/reencodar audio) — depois de
  instalar, **feche e abra um terminal novo** pra ele reconhecer o PATH
- **spotdl >= 4.5.2** — versoes mais antigas tem um bug conhecido que trava
  pra sempre em "Processing query" ([issue #2587](https://github.com/spotDL/spotify-downloader/issues/2587)).
  O `requirements.txt` ja pede essa versao ou mais nova.
- Uma app do Spotify criada em https://developer.spotify.com/dashboard (gratis)
  pra obter `SPOTIFY_CLIENT_ID` e `SPOTIFY_CLIENT_SECRET`, com
  `http://127.0.0.1:8000/callback` cadastrado como Redirect URI (usado pelo
  botao "Conectar com Spotify")

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edite o `.env` e preencha `SPOTIFY_CLIENT_ID` e `SPOTIFY_CLIENT_SECRET`.

## Rodando

No Windows (PowerShell), o jeito mais simples e rodar o script pronto, que ja
chama o uvicorn de dentro do `.venv` sem precisar ativar nada:

```powershell
.\run.ps1
```

Ou manualmente:

```bash
.venv\Scripts\uvicorn.exe app.main:app --reload
```

Acesse http://localhost:8000

Os arquivos baixados ficam em `downloads/<job_id>/` e são apagados
automaticamente após `FILE_TTL_SECONDS` (padrão 30 min, configuravel no
`.env`) — entao mova o que quiser guardar pra outro lugar depois de baixar.

## Hospedando (Railway)

O app roda via Docker (o `Dockerfile` ja instala ffmpeg junto). Pra hospedar
no [Railway](https://railway.app):

1. Crie um projeto novo no Railway e conecte esse repositorio (voce faz login
   e clica em "Deploy" — isso e uma etapa que so voce pode fazer)
2. Nas variaveis de ambiente do projeto, configure `SPOTIFY_CLIENT_ID` e
   `SPOTIFY_CLIENT_SECRET`, e **defina `BASIC_AUTH_USER` e
   `BASIC_AUTH_PASSWORD`** — sem isso o site fica acessivel pra qualquer um
   que descobrir a URL, ja que nao ha tela de login
3. O Railway detecta o `Dockerfile` automaticamente e expoe a porta via `$PORT`
   (ja tratado no `CMD` do Dockerfile)

Localmente essas duas variaveis ficam em branco (uso sem senha), entao isso
so afeta a versao hospedada.

## Uso pessoal, nao redistribua

O audio baixado é só pra uso pessoal. Nao faz parte deste repositorio, nao deve
ser hospedado publicamente, nem vendido/redistribuido — isso e o que separa uma
ferramenta pessoal de backup offline de um servico de pirataria comercial.

## Estrutura

```
app/
  main.py                 # app FastAPI, rotas estaticas, rate limit
  config.py                # variaveis de ambiente
  logging_config.py         # grava app.log (gitignored) pra debug
  routers/
    search.py              # GET /api/search
    download.py             # POST /api/download, status e arquivo
    preview.py               # GET /api/bpm, /api/bpm-spotify, /api/bpm-youtube, /api/trending, /api/history
    auth.py                  # GET /auth/login, /callback, /auth/status
  services/
    spotify_search.py      # busca via spotipy + audio-features (autenticado)
    spotify_auth.py          # login PKCE com Spotify
    spotdl_service.py         # download via spotdl (subprocess)
    youtube_service.py        # busca e download via yt-dlp
    bpm_service.py             # estimativa de bpm via librosa
    history_service.py         # historico local de downloads (json)
    jobs.py                    # fila de jobs em memoria + limpeza
  templates/index.html
  static/style.css, app.js
downloads/                  # arquivos temporarios + historico (gitignored)
run.ps1                     # atalho pra rodar o servidor (Windows/PowerShell)
Dockerfile                  # build pra hospedar (ex: Railway)
```
