# djs-best-friend

Site em Python (FastAPI) pra buscar musicas e baixar o audio na melhor qualidade
disponivel, com duas fontes:

- **Spotify** (via [spotdl](https://github.com/spotDL/spotify-downloader)): busca
  metadados no Spotify, baixa o audio correspondente no YouTube Music e reencoda
  para mp3 320kbps, com capa/artista/album embutidos.
- **YouTube** (via [yt-dlp](https://github.com/yt-dlp/yt-dlp) direto): baixa o
  melhor stream de audio disponivel **sem reencodar**, preservando o bitrate real
  da fonte.

## Sobre qualidade de audio

Nenhum desses caminhos baixa do "servidor original" do Spotify — o Spotify não
expõe os arquivos de audio brutos. Tanto o spotdl quanto o modo YouTube direto
buscam o audio no YouTube/YouTube Music, cujo stream de audio normalmente já vem
limitado a algo entre 128-160kbps (opus/AAC). Reencodar para 320kbps kbps não
recupera qualidade que não estava lá — só aumenta o tamanho do arquivo. Por isso
o site oferece as duas opções: "original" pra quem quer o stream cru sem
retrabalho, e "320k mp3" pra quem quer compatibilidade máxima (tocadores antigos,
metadados/capa embutidos) mesmo sabendo que o teto de qualidade é o mesmo.

## Requisitos

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html) instalado e no PATH (usado pelo
  spotdl e pelo yt-dlp pra extrair/reencodar audio)
- Uma app do Spotify criada em https://developer.spotify.com/dashboard (gratis)
  pra obter `SPOTIFY_CLIENT_ID` e `SPOTIFY_CLIENT_SECRET`

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edite o `.env` e preencha `SPOTIFY_CLIENT_ID` e `SPOTIFY_CLIENT_SECRET`.

## Rodando localmente

```bash
uvicorn app.main:app --reload
```

Acesse http://localhost:8000

## Rodando acessivel na rede/internet

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Antes de expor isso publicamente na internet**, vale considerar:

- Baixar musica protegida por direitos autorais sem autorização pode violar os
  Termos de Serviço do Spotify/YouTube e, dependendo do uso, a legislação de
  direitos autorais local. Este projeto é pensado para uso pessoal/backup
  offline de conteúdo que você já tem direito de ouvir.
- O rate limit em `app/main.py` (`RATE_LIMIT_PER_MINUTE`) é bem simples
  (por IP, em memória) — não segura um uso público de verdade sozinho.
- Não existe autenticação. Se for expor na internet, recomendo colocar atrás de
  login (ex: reverse proxy com Basic Auth) para não virar um serviço público
  anônimo de download.
- Os arquivos baixados ficam em `downloads/<job_id>/` e são apagados
  automaticamente após `FILE_TTL_SECONDS` (padrão 30 min).

## Estrutura

```
app/
  main.py              # app FastAPI, rotas estaticas, rate limit
  config.py             # variaveis de ambiente
  routers/
    search.py           # GET /api/search
    download.py          # POST /api/download, status e arquivo
  services/
    spotify_search.py   # busca via spotipy
    spotdl_service.py    # download via spotdl (subprocess)
    youtube_service.py   # busca e download via yt-dlp
    jobs.py              # fila de jobs em memoria + limpeza
  templates/index.html
  static/style.css, app.js
downloads/               # arquivos temporarios (gitignored)
```
