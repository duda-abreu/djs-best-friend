# DJ's Best Friend

Ferramenta pessoal para pesquisar faixas, ouvir prévias, ver BPM e preparar referências para sets de DJ, com uma interface inspirada em aparelhos de som dos anos 2000.

**Versão online:** https://duda-abreu.github.io/djs-best-friend/ (busca + prévia oficial de 30s, sem download)

## Duas versões

| | Online (GitHub Pages) | Local (FastAPI) |
|---|---|---|
| Busca de músicas | iTunes Search API | Spotify e YouTube |
| Ouvir prévia | prévia oficial de 30s | prévia do Spotify ou embed do YouTube |
| Faixa completa | link pro Apple Music | download pessoal via spotdl / yt-dlp |
| BPM | o do Beatport, nas faixas em alta | do Beatport ou estimado localmente (librosa) |
| "Em alta essa semana" | sim, atualizada toda sexta pelo GitHub Actions | Top 100 do Beatport (house, tech house, techno, melodic), ao vivo |
| Histórico de downloads | não | sim, com opção de excluir |
| Precisa de chaves de API | não | sim |

A versão online é 100% estática (pasta [`docs/`](docs)) e só usa fontes que permitem esse uso. O download fica somente na versão local porque depende de ferramentas instaladas na sua máquina e é de uso pessoal.

## Recursos (versão local)

- Busca por música ou artista no Spotify ou YouTube, com 10, 20 ou 50 resultados.
- Prévia antes de baixar.
- Duração e BPM em cada resultado. O BPM é estimado com `librosa` e corrigido para erros de oitava (por exemplo 80 detectado quando o real é 120).
- Download em MP3 320 kbps (Spotify via spotdl) ou no áudio original do YouTube.
- "Em alta essa semana": os Top 100 de house, tech house, techno e melodic house & techno do Beatport, intercalados por posição e ligados às faixas do Spotify. Automático, sem lista fixa de artistas, e já traz o BPM oficial do Beatport. Se o Beatport falhar, cai pro Last.fm e depois pra uma lista fixa.
- Painel "tocando agora" com progresso do download.
- Histórico local com total de músicas, GB e últimos 7 dias, com exclusão de arquivos.
- Login opcional com Spotify (PKCE, sem client secret no navegador).

## Como funciona

```
navegador ──> FastAPI ──> Spotify API / Last.fm / YouTube
                 │
                 └──> jobs em background ──> spotdl / yt-dlp + ffmpeg ──> downloads/
```

- `app/services/spotify_search.py`: busca e lógica do "em alta" (Beatport, depois Last.fm, depois lista fixa).
- `app/services/beatport_service.py`: lê os charts de gênero do Beatport (cache de 1h).
- `app/services/lastfm_service.py`: tags e top tracks do Last.fm (fallback).
- `app/services/bpm_service.py`: estimativa de BPM.
- `app/services/jobs.py`: fila de downloads com timeout.
- `app/services/history_service.py`: histórico em `downloads/history.json`.
- `app/static/` e `app/templates/`: interface.

## Rodar localmente

Requer Python 3.11+, [FFmpeg](https://ffmpeg.org/) no PATH e chaves próprias:

- **Spotify:** crie um app em https://developer.spotify.com/dashboard e cadastre `http://127.0.0.1:8000/callback` como Redirect URI.
- **Last.fm:** crie uma chave grátis em https://www.last.fm/api/account/create.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Preencha o `.env` com suas chaves (o arquivo não vai pro Git):

```env
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
LASTFM_API_KEY=
```

Inicie e acesse `http://127.0.0.1:8000`:

```powershell
.\run.ps1
```

> Use `python -m pip` em vez de só `pip`. Se você tem ferramentas que interceptam o comando `pip` (como o Safety CLI), a instalação pode travar.

### Variáveis opcionais

| Variável | Padrão | Para quê |
|---|---|---|
| `SPOTIFY_REDIRECT_URI` | `http://127.0.0.1:8000/callback` | login com Spotify |
| `DOWNLOAD_DIR` | `downloads` | onde os arquivos ficam |
| `RATE_LIMIT_PER_MINUTE` | `6` | downloads por minuto por IP |
| `BASIC_AUTH_USER` / `BASIC_AUTH_PASSWORD` | vazio | senha HTTP Basic, obrigatória se expuser o app fora do seu computador |

O `Dockerfile` serve para rodar em um servidor **privado**. Se hospedar em qualquer endereço acessível pela internet, defina `BASIC_AUTH_USER` e `BASIC_AUTH_PASSWORD`.

## Publicar a versão online no GitHub Pages

1. No repositório, abra **Settings > Pages**.
2. Em **Source**, escolha **Deploy from a branch**.
3. Selecione a branch `main` e a pasta `/docs`, e salve.
4. Após alguns minutos o site fica em `https://<usuario>.github.io/djs-best-friend/`.

O GitHub Pages só serve arquivos estáticos, então o backend Python não roda lá.

### Em alta na versão online

O navegador não consegue ler o Beatport direto, então o workflow [`update-trending.yml`](.github/workflows/update-trending.yml) roda `scripts/update_trending.py` toda sexta às 12h UTC. Ele lê os charts do Beatport, liga cada faixa à iTunes Search API (capa, prévia, link) e grava `docs/trending.json`, que a página lê. Para atualizar na hora: aba **Actions > Atualiza em alta da semana > Run workflow**. Se o Beatport bloquear o GitHub ou mudar o site, o workflow falha e a página continua com a última lista. O `docs/style.css` é uma cópia de `app/static/style.css`; se mudar o visual do app, copie de novo.

## Limitações conhecidas

- **Spotify em modo de desenvolvimento:** apps novos não acessam `audio-features`, `artists/{id}/top-tracks` nem playlists de terceiros (como a "mint"), e a busca é limitada a 10 resultados por chamada. Por isso o BPM é calculado localmente quando a faixa não vem do Beatport.
- **"Em alta" via Beatport:** não há API pública, então o app lê os dados embutidos na página do chart. Se o Beatport mudar o site, o app cai pro fallback do Last.fm (`tag.getTopTracks`, ranking de todos os tempos, com clássicos antigos misturados). Faixas que não existem no Spotify ficam de fora.
- **Correspondência de áudio:** o Spotify não fornece o áudio. O spotdl procura a faixa no YouTube Music, então pode vir uma versão diferente (remix, ao vivo).
- **BPM estimado:** em intros, mudanças de andamento e faixas com batida em meio tempo pode errar.
- **APIs de terceiros** (Spotify, YouTube, Last.fm) mudam sem aviso, e os fallbacks podem quebrar.

## Aviso legal

Projeto independente, sem vínculo com Spotify, YouTube, Last.fm ou Apple. O download é para uso pessoal e apenas de conteúdo próprio, licenciado ou autorizado. Você é responsável por respeitar direitos autorais e os termos de uso de cada plataforma. Não use este projeto para redistribuir, vender ou hospedar áudio protegido.
