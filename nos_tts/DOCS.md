# Nós TTS

**[English](#english) · [Galego](#galego) · [Castellano](#castellano)**

| Voice / Voz | Model / Modelo |
|---|---|
| `celtia` ♀ | [proxectonos/Nos_TTS-celtia-vits-graphemes](https://huggingface.co/proxectonos/Nos_TTS-celtia-vits-graphemes) (gated / restrinxido / restringido) |
| `brais` ♂ | [proxectonos/Nos_TTS-brais-vits-graphemes](https://huggingface.co/proxectonos/Nos_TTS-brais-vits-graphemes) |

---

## English

Wyoming text-to-speech server with the Galician voices of Proxecto Nós. The voices speak **Galician only** (that is the language they were trained on). The add-on's page, **Voces Nós**, is available in Galician, Spanish and English: it follows Home Assistant's language and can be changed from the selector at the top right.

### Getting started

1. Start the add-on and open **Voces Nós** in the sidebar (or **Open web UI** on the add-on page).
2. In the **Install** tab, click **Install** next to Brais. The add-on downloads the 1 GB model itself; it takes a few minutes.
3. Celtia is a gated model:
   1. Open the [model page](https://huggingface.co/proxectonos/Nos_TTS-celtia-vits-graphemes) with your Hugging Face account and accept its conditions.
   2. Create a *Read* token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
   3. Paste the token in the page and click **Install** next to Celtia. The token is only used for that download and is not stored.
4. Add the **Wyoming Protocol** integration with the add-on's host name (for example `local-nos-tts`, shown on the add-on page) and port `10200`. When voices are installed or deleted, the add-on reloads that integration by itself.

### The Voces Nós page

- **Voices**: installed voices, size and status; make one the default, try it or delete it.
- **Install**: the known voices with one click, any other Hugging Face repository with a Coqui VITS model (`.pth` + `config.json`), or upload your own files. If uploading such large files fails, copy them to `/share/nos_tts/<name>/` (Samba or SSH) and restart the add-on.
- **Try**: type a text, listen to it with any voice and download it as WAV.
- **Pronunciation & settings**: edit `pronuncia.txt` and `ajustes.txt` (see below). Saving them, or changing the default voice, clears Home Assistant's TTS cache so you hear the change at once.

### Files

Everything is stored in `/share/nos_tts/`:

```
/share/nos_tts/
├── celtia/          celtia.pth, config.json, voz.json
├── brais/           brais.pth, config.json, voz.json
├── pronuncia.txt    (optional)
└── ajustes.txt      (optional)
```

Every subfolder holding a `.pth` and a `config.json` is a voice, named after the folder. The default voice is the one set with `defecto = name` in `ajustes.txt` (or the **Make default** button); otherwise `celtia` if installed, otherwise the first one alphabetically.

### Using it in Home Assistant

Entity `tts.nos_tts` (the name depends on the integration), language `gl`. Choose the voice with the `voice` option:

```yaml
action: tts.speak
target:
  entity_id: tts.nos_tts
data:
  media_player_entity_id: media_player.living_room
  language: gl
  message: "Benvidos ao Centro."
  options:
    voice: brais
```

**Languages.** Each voice declares its own language (`idioma` in its `voz.json`, `gl` by default) and, unless you turn it off in the **Voices** tab (`idioma_ha = no` in `ajustes.txt`), also Home Assistant's system language. That is only so the *Media > Text-to-speech* form shows the voice selector: it only preselects a language matching the system one. The voices still speak Galician.

### Pronunciation dictionary: `pronuncia.txt`

Fixes words a voice says wrong. One rule per line, `word = how it should be read`. Rules apply to whole words and are case-insensitive; `#` starts a comment.

```
USC = u ese ce
```

### Per-voice settings: `ajustes.txt`

Each line is `voice.key = value` (that voice only) or `key = value` (all voices). The key names are in Galician/Spanish:

| Key | Default | Effect |
|---|---|---|
| `ruido` | 0.5 | Intonation variation (the original model uses 0.667). |
| `ruido_duracion` | 0.3 | Variation in sound durations (original: 1.0). When high, syllables are sometimes dropped. |
| `velocidad` | 1 | Above 1 speaks faster. |
| `semilla` | 1234 | Fixes the randomness: the same sentence always gives the same audio. |
| `motor` | torch | `onnx` (experimental): about twice as fast on a Pi 5, with the same reproducible audio. The first time, it converts the voice to `<voice>.onnx` (about 115 MB, a few seconds). It can also be switched per voice from the **Engine** column of the Voices tab. |
| `defecto` | | Default voice (global only). |

Both files are re-read as soon as they change, without restarting.

### Text normalisation

The models were trained on text normalised by [Cotovía](http://gtm.uvigo.es/en/transfer/software/cotovia/), which only exists for amd64. This add-on does not use it. Instead it:

- converts numbers to Galician words (0 to 999 999; longer numbers are read digit by digit);
- removes characters that are not in the model's vocabulary;
- lowercases the text for voices whose `config.json` has no `text_cleaner` (Brais). With capitals, Brais drops the first consonant ("entro" for "Centro").

Abbreviations, dates and acronyms are not expanded: add them to `pronuncia.txt`.

### Security

The page only answers through Home Assistant's ingress, so only signed-in users can reach it. The Hugging Face token is never stored.

---

## Galego

Servidor Wyoming de texto a voz coas voces galegas do Proxecto Nós. As voces falan **só galego** (é a lingua coa que se adestraron). A páxina do complemento, **Voces Nós**, está en galego, castelán e inglés: segue a lingua de Home Assistant e pódese cambiar no selector de arriba á dereita.

### Primeiros pasos

1. Arrinca o complemento e abre **Voces Nós** na barra lateral (ou **Abrir interface web** na páxina do complemento).
2. Na lapela **Instalar**, preme **Instalar** en Brais. O complemento descarga el mesmo o modelo, de 1 GB; tarda uns minutos.
3. Celtia ten acceso restrinxido:
   1. Entra na [páxina do modelo](https://huggingface.co/proxectonos/Nos_TTS-celtia-vits-graphemes) coa túa conta de Hugging Face e acepta as condicións.
   2. Crea un token de tipo *Read* en [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
   3. Pega o token na páxina e preme **Instalar** en Celtia. O token só se usa para esa descarga e non se garda.
4. Engade a integración **Wyoming Protocol** co host do complemento (por exemplo `local-nos-tts`, aparece na páxina do complemento) e o porto `10200`. Ao instalar ou borrar voces, o complemento recarga esa integración por si só.

### A páxina «Voces Nós»

- **Voces**: voces instaladas, tamaño e estado; escoller a voz por defecto, probala ou borrala.
- **Instalar**: as voces coñecidas cun clic, calquera outro repositorio de Hugging Face cun modelo Coqui VITS (`.pth` + `config.json`) ou subir os teus propios ficheiros. Se a subida de ficheiros tan grandes falla, cópiaos a `/share/nos_tts/<nome>/` (Samba ou SSH) e reinicia o complemento.
- **Probar**: escribe un texto, escóitao con calquera voz e descárgao en WAV.
- **Pronuncia e axustes**: edita `pronuncia.txt` e `ajustes.txt` (velaquí abaixo). Ao gardalos, ou ao cambiar a voz por defecto, baléirase a caché de TTS de Home Assistant para oír o cambio no momento.

### Ficheiros

Todo se garda en `/share/nos_tts/`:

```
/share/nos_tts/
├── celtia/          celtia.pth, config.json, voz.json
├── brais/           brais.pth, config.json, voz.json
├── pronuncia.txt    (opcional)
└── ajustes.txt      (opcional)
```

Cada subcartafol cun `.pth` e un `config.json` é unha voz, co nome do cartafol. A voz por defecto é a indicada con `defecto = nome` en `ajustes.txt` (ou co botón **Usar por defecto**); se non, `celtia` se está instalada; se non, a primeira por orde alfabética.

### Uso en Home Assistant

Entidade `tts.nos_tts` (o nome depende da integración), lingua `gl`. A voz escóllese coa opción `voice`:

```yaml
action: tts.speak
target:
  entity_id: tts.nos_tts
data:
  media_player_entity_id: media_player.salon
  language: gl
  message: "Benvidos ao Centro."
  options:
    voice: brais
```

**Linguas.** Cada voz declara a súa lingua (`idioma` no seu `voz.json`; `gl` por defecto) e, salvo que o desactives na lapela **Voces** (`idioma_ha = no` en `ajustes.txt`), tamén a lingua do sistema de Home Assistant. Só serve para que o formulario de *Multimedia > Texto a voz* amose o selector de voces: ese formulario só preselecciona unha lingua que coincida coa do sistema. As voces seguen falando galego.

### Dicionario de pronuncia: `pronuncia.txt`

Corrixe palabras que unha voz pronuncia mal. Unha regra por liña, `palabra = como se debe ler`. As regras aplícanse a palabras completas e non distinguen maiúsculas; `#` inicia un comentario.

```
USC = u ese ce
```

### Axustes por voz: `ajustes.txt`

Cada liña é `voz.clave = valor` (só para esa voz) ou `clave = valor` (para todas):

| Clave | Por defecto | Efecto |
|---|---|---|
| `ruido` | 0.5 | Variación da entoación (o modelo orixinal usa 0.667). |
| `ruido_duracion` | 0.3 | Variación da duración dos sons (orixinal: 1.0). Se é alta, ás veces come sílabas. |
| `velocidad` | 1 | Por riba de 1 fala máis rápido. |
| `semilla` | 1234 | Fixa a aleatoriedade: a mesma frase dá sempre o mesmo audio. |
| `motor` | torch | `onnx` (experimental): arredor do dobre de rápido nunha Pi 5, co mesmo audio reproducible. A primeira vez converte a voz a `<voz>.onnx` (uns 115 MB, uns segundos). Tamén se cambia por voz desde a columna **Motor** da lapela Voces. |
| `defecto` | | Voz por defecto (só global). |

Os dous ficheiros volven lerse en canto cambian, sen reiniciar.

### Normalización do texto

Os modelos adestráronse con texto normalizado por [Cotovía](http://gtm.uvigo.es/en/transfer/software/cotovia/), que só existe para amd64. Este complemento non o usa. No seu lugar:

- converte os números a palabras en galego (de 0 a 999 999; os números máis longos lense cifra a cifra);
- elimina os caracteres que non están no vocabulario do modelo;
- pasa o texto a minúsculas nas voces cuxo `config.json` non ten `text_cleaner` (Brais). Con maiúsculas, Brais come a primeira consoante ("entro" por "Centro").

As abreviaturas, datas e siglas non se expanden: engádeas a `pronuncia.txt`.

### Seguranza

A páxina só responde a través do ingress de Home Assistant, é dicir, só a usuarios con sesión iniciada. O token de Hugging Face non se garda en ningún sitio.

---

## Castellano

Servidor Wyoming de texto a voz con las voces gallegas del Proxecto Nós. Las voces hablan **solo gallego** (es el idioma con el que se entrenaron). La página del complemento, **Voces Nós**, está en gallego, castellano e inglés: sigue el idioma de Home Assistant y se puede cambiar en el selector de arriba a la derecha.

### Primeros pasos

1. Arranca el complemento y abre **Voces Nós** en la barra lateral (o **Abrir interfaz web** en la página del complemento).
2. En la pestaña **Instalar**, pulsa **Instalar** en Brais. El complemento descarga él mismo el modelo, de 1 GB; tarda unos minutos.
3. Celtia tiene acceso restringido:
   1. Entra en la [página del modelo](https://huggingface.co/proxectonos/Nos_TTS-celtia-vits-graphemes) con tu cuenta de Hugging Face y acepta las condiciones.
   2. Crea un token de tipo *Read* en [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
   3. Pega el token en la página y pulsa **Instalar** en Celtia. El token solo se usa para esa descarga y no se guarda.
4. Añade la integración **Wyoming Protocol** con el host del complemento (por ejemplo `local-nos-tts`, aparece en la página del complemento) y el puerto `10200`. Al instalar o borrar voces, el complemento recarga esa integración por sí solo.

### La página «Voces Nós»

- **Voces**: voces instaladas, tamaño y estado; elegir la voz por defecto, probarla o borrarla.
- **Instalar**: las voces conocidas con un clic, cualquier otro repositorio de Hugging Face con un modelo Coqui VITS (`.pth` + `config.json`) o subir tus propios archivos. Si la subida de archivos tan grandes falla, cópialos a `/share/nos_tts/<nombre>/` (Samba o SSH) y reinicia el complemento.
- **Probar**: escribe un texto, escúchalo con cualquier voz y descárgalo en WAV.
- **Pronuncia y ajustes**: edita `pronuncia.txt` y `ajustes.txt` (ver más abajo). Al guardarlos, o al cambiar la voz por defecto, se vacía la caché de TTS de Home Assistant para oír el cambio al momento.

### Archivos

Todo se guarda en `/share/nos_tts/`:

```
/share/nos_tts/
├── celtia/          celtia.pth, config.json, voz.json
├── brais/           brais.pth, config.json, voz.json
├── pronuncia.txt    (opcional)
└── ajustes.txt      (opcional)
```

Cada subcarpeta con un `.pth` y un `config.json` es una voz, con el nombre de la carpeta. La voz por defecto es la indicada con `defecto = nombre` en `ajustes.txt` (o con el botón **Usar por defecto**); si no, `celtia` si está instalada; si no, la primera por orden alfabético.

### Uso en Home Assistant

Entidad `tts.nos_tts` (el nombre depende de la integración), idioma `gl`. La voz se elige con la opción `voice`:

```yaml
action: tts.speak
target:
  entity_id: tts.nos_tts
data:
  media_player_entity_id: media_player.salon
  language: gl
  message: "Benvidos ao Centro."
  options:
    voice: brais
```

**Idiomas.** Cada voz declara su idioma (`idioma` en su `voz.json`; `gl` por defecto) y, salvo que lo desactives en la pestaña **Voces** (`idioma_ha = no` en `ajustes.txt`), también el idioma del sistema de Home Assistant. Solo sirve para que el formulario de *Multimedia > Texto a voz* muestre el selector de voces: ese formulario solo preselecciona un idioma que coincida con el del sistema. Las voces siguen hablando gallego.

### Diccionario de pronuncia: `pronuncia.txt`

Corrige palabras que una voz pronuncia mal. Una regla por línea, `palabra = como se debe leer`. Las reglas se aplican a palabras completas y no distinguen mayúsculas; `#` inicia un comentario.

```
USC = u ese ce
```

### Ajustes por voz: `ajustes.txt`

Cada línea es `voz.clave = valor` (solo para esa voz) o `clave = valor` (para todas):

| Clave | Por defecto | Efecto |
|---|---|---|
| `ruido` | 0.5 | Variación de la entonación (el modelo original usa 0.667). |
| `ruido_duracion` | 0.3 | Variación de la duración de los sonidos (original: 1.0). Si es alta, a veces se come sílabas. |
| `velocidad` | 1 | Por encima de 1 habla más rápido. |
| `semilla` | 1234 | Fija la aleatoriedad: la misma frase da siempre el mismo audio. |
| `motor` | torch | `onnx` (experimental): alrededor del doble de rápido en una Pi 5, con el mismo audio reproducible. La primera vez convierte la voz a `<voz>.onnx` (unos 115 MB, unos segundos). También se cambia por voz desde la columna **Motor** de la pestaña Voces. |
| `defecto` | | Voz por defecto (solo global). |

Los dos archivos se vuelven a leer en cuanto cambian, sin reiniciar.

### Normalización del texto

Los modelos se entrenaron con texto normalizado por [Cotovía](http://gtm.uvigo.es/en/transfer/software/cotovia/), que solo existe para amd64. Este complemento no lo usa. En su lugar:

- convierte los números a palabras en gallego (de 0 a 999 999; los números más largos se leen cifra a cifra);
- elimina los caracteres que no están en el vocabulario del modelo;
- pasa el texto a minúsculas en las voces cuyo `config.json` no tiene `text_cleaner` (Brais). Con mayúsculas, Brais se come la primera consonante ("entro" por "Centro").

Las abreviaturas, fechas y siglas no se expanden: añádelas a `pronuncia.txt`.

### Seguridad

La página solo responde a través del ingress de Home Assistant, es decir, solo a usuarios con sesión iniciada. El token de Hugging Face no se guarda en ningún sitio.
