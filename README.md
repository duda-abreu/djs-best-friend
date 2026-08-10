# DJ's Best Friend

Ferramenta pessoal para pesquisar faixas, ouvir prévias, estimar BPM e preparar referências para sets de DJ. A busca usa Spotify e Last.fm; prévias e downloads podem usar YouTube como alternativa.

## Ideia geral

O projeto tenta reunir em uma tela o fluxo de descoberta musical:

- buscar músicas e artistas;
- encontrar faixas de house e techno em alta;
- ouvir uma prévia;
- estimar BPM;
- baixar uma referência e manter histórico local.

É um protótipo para uso pessoal, não um serviço de distribuição de música.

## Por que é difícil manter

- A API do Spotify muda permissões, limites e endpoints. Recursos como `audio-features`, prévias e acesso a playlists podem retornar `403`, desaparecer ou exigir autenticação de usuário.
- Aplicações novas podem ter acesso mais restrito que integrações antigas. Algo que funciona em uma conta pode falhar em outra.
- O Spotify não fornece o áudio completo. O projeto depende de correspondência com vídeos externos, que pode encontrar versão errada, remix, gravação ao vivo ou áudio com qualidade diferente.
- Downloads e redistribuição envolvem direitos autorais e termos de uso das plataformas. O usuário precisa ter autorização sobre qualquer conteúdo obtido.
- YouTube, Spotify e Last.fm podem alterar páginas, APIs, limites e regras sem aviso. Isso torna os fallbacks frágeis.
- Estimativa de BPM por trecho não é exata, principalmente em intros, mudanças de andamento e detecção em meio ou dobro do BPM real.

Essas limitações dificultam transformar o protótipo em produto público estável. O caminho mais seguro seria manter foco em descoberta, metadados e links oficiais, sem hospedar ou redistribuir áudio protegido.

## Rodar localmente

Requer Python 3.11+, FFmpeg e credenciais próprias do Spotify.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Crie `.env` na raiz:

```env
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
LASTFM_API_KEY=
```

Inicie:

```powershell
.\run.ps1
```

Acesse `http://127.0.0.1:8000`.

## Aviso

Use apenas conteúdo próprio, licenciado ou autorizado. Respeite direitos autorais e termos do Spotify, YouTube e Last.fm.
