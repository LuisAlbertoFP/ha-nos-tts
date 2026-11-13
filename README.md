# Nós TTS for Home Assistant

**[English](#english) · [Galego](#galego) · [Castellano](#castellano)**

| Add-on | |
|---|---|
| [Nós TTS](nos_tts) | Wyoming TTS server with Coqui VITS and the `Nos_TTS-*-vits-graphemes` models · Servidor Wyoming TTS con Coqui VITS e os modelos `Nos_TTS-*-vits-graphemes` |

---

## English

Home Assistant add-on repository with the Galician voices **Celtia** (female) and **Brais** (male) from [Proxecto Nós](https://nos.gal/gl/proxecto-nos) (University of Santiago de Compostela).

The voices run **locally, without internet**, and plug into Home Assistant as a [Wyoming](https://www.home-assistant.io/integrations/wyoming/) server, so they work like Piper: in Assist, in automations (`tts.speak`) or in any integration that uses TTS. They speak Galician only; the add-on's management page is in Galician, Spanish and English.

### Installation

1. In Home Assistant: **Settings > Add-ons > Add-on store**. In the ⋮ menu choose **Repositories** and add this repository's URL.
2. Install **Nós TTS** and start it. The first build takes a while, because it downloads and installs PyTorch.
3. Open **Voces Nós** in the sidebar and install the voices from there (they are downloaded from Hugging Face). Celtia needs a read token from your Hugging Face account, after accepting its conditions.
4. Go to **Settings > Devices & services > Add integration > Wyoming Protocol**, with the add-on's host name and port `10200`.

More details in [the documentation](nos_tts/DOCS.md).

### Requirements

- Home Assistant OS or Supervised, **aarch64** (tested on a Raspberry Pi 5 with 8 GB).
- About 4 GB free for the image (PyTorch) and 1 GB per voice.
- On a Pi 5, synthesis takes about as long as the audio lasts (RTF ≈ 0.8). Home Assistant's TTS cache makes repeated phrases instant.

### Credits and licences

- Models: [Proxecto Nós](https://huggingface.co/proxectonos), Apache-2.0. Celtia is gated: you must accept its conditions on Hugging Face. The models are **not** included in this repository.
- Engine: [coqui-tts](https://github.com/idiap/coqui-ai-TTS) (MPL-2.0).
- Protocol: [wyoming](https://github.com/rhasspy/wyoming) (MIT).
- This add-on: [Apache-2.0](LICENSE).

---

## Galego

Repositorio de complementos de Home Assistant coas voces galegas **Celtia** (muller) e **Brais** (home) do [Proxecto Nós](https://nos.gal/gl/proxecto-nos) (Universidade de Santiago de Compostela).

As voces execútanse **en local, sen internet**, e intégranse en Home Assistant como un servidor [Wyoming](https://www.home-assistant.io/integrations/wyoming/), así que funcionan coma Piper: en Assist, en automatizacións (`tts.speak`) ou en calquera integración que use TTS. Falan só galego; a páxina de xestión do complemento está en galego, castelán e inglés.

### Instalación

1. En Home Assistant: **Axustes > Complementos > Tenda de complementos**. No menú ⋮ escolle **Repositorios** e engade o URL deste repositorio.
2. Instala **Nós TTS** e arríncao. A primeira construción tarda bastante, porque descarga e instala PyTorch.
3. Abre **Voces Nós** na barra lateral e instala as voces desde alí (descárganse de Hugging Face). Celtia precisa un token de lectura da túa conta de Hugging Face, despois de aceptar as súas condicións.
4. Vai a **Axustes > Dispositivos e servizos > Engadir integración > Wyoming Protocol**, co host do complemento e o porto `10200`.

Máis detalles na [documentación](nos_tts/DOCS.md#galego).

### Requisitos

- Home Assistant OS ou Supervised, **aarch64** (probado nunha Raspberry Pi 5 de 8 GB).
- Uns 4 GB libres para a imaxe (PyTorch) e 1 GB por voz.
- Nunha Pi 5, a síntese tarda aproximadamente o mesmo que dura o audio (RTF ≈ 0,8). A caché de TTS de Home Assistant fai que as frases repetidas saian ao instante.

### Créditos e licenzas

- Modelos: [Proxecto Nós](https://huggingface.co/proxectonos), Apache-2.0. Celtia ten acceso restrinxido: hai que aceptar as súas condicións en Hugging Face. Os modelos **non** se inclúen neste repositorio.
- Motor: [coqui-tts](https://github.com/idiap/coqui-ai-TTS) (MPL-2.0).
- Protocolo: [wyoming](https://github.com/rhasspy/wyoming) (MIT).
- Este complemento: [Apache-2.0](LICENSE).

---


## Castellano

Repositorio de complementos de Home Assistant con las voces gallegas **Celtia** (mujer) y **Brais** (hombre) del [Proxecto Nós](https://nos.gal/gl/proxecto-nos) (Universidad de Santiago de Compostela).

Las voces se ejecutan **en local, sin internet**, y se integran en Home Assistant como un servidor [Wyoming](https://www.home-assistant.io/integrations/wyoming/), así que funcionan como Piper: en Assist, en automatizaciones (`tts.speak`) o en cualquier integración que use TTS. Hablan solo gallego; la página de gestión del complemento está en gallego, castellano e inglés.

### Instalación

1. En Home Assistant: **Ajustes > Complementos > Tienda de complementos**. En el menú ⋮ elige **Repositorios** y añade la URL de este repositorio.
2. Instala **Nós TTS** y arráncalo. La primera construcción tarda bastante, porque descarga e instala PyTorch.
3. Abre **Voces Nós** en la barra lateral e instala las voces desde allí (se descargan de Hugging Face). Celtia necesita un token de lectura de tu cuenta de Hugging Face, después de aceptar sus condiciones.
4. Ve a **Ajustes > Dispositivos y servicios > Añadir integración > Wyoming Protocol**, con el host del complemento y el puerto `10200`.

Más detalles en [la documentación](nos_tts/DOCS.md#castellano).

### Requisitos

- Home Assistant OS o Supervised, **aarch64** (probado en una Raspberry Pi 5 de 8 GB).
- Unos 4 GB libres para la imagen (PyTorch) y 1 GB por voz.
- En una Pi 5, la síntesis tarda aproximadamente lo mismo que dura el audio (RTF ≈ 0,8). La caché de TTS de Home Assistant hace que las frases repetidas salgan al instante.

### Créditos y licencias

- Modelos: [Proxecto Nós](https://huggingface.co/proxectonos), Apache-2.0. Celtia tiene acceso restringido: hay que aceptar sus condiciones en Hugging Face. Los modelos **no** se incluyen en este repositorio.
- Motor: [coqui-tts](https://github.com/idiap/coqui-ai-TTS) (MPL-2.0).
- Protocolo: [wyoming](https://github.com/rhasspy/wyoming) (MIT).
- Este complemento: [Apache-2.0](LICENSE).
