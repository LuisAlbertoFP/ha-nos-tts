# Changelog

## 0.4.3

- Pages from 0.4.1 or earlier still cached by the browser for Home Assistant's iframe now jump to the current page by themselves. The server spots them because they do not send the `X-Nos-Web` header.
- The engine name of a voice that is not loaded is now escaped.

## 0.4.2

- The add-on page is now a small loader that fetches the real page (`app.html`) with JavaScript, bypassing the browser cache. Home Assistant shows it inside an iframe, and browsers cache iframe documents separately, so an old copy could linger after an update.

## 0.4.1

- The Voices tab shows each voice's language in its own column (name and code).
- The page is served with `Cache-Control: no-cache`, so browsers load the new version after an update.

## 0.4.0

- Declared languages now come from the installed voices (`idioma` in each `voz.json`, `gl` by default) plus, optionally, Home Assistant's system language, read from Core and checked every 10 minutes. The extra language is on by default and can be turned off in the Voices tab (`idioma_ha = no` in `ajustes.txt`). It replaces the fixed `gl,es,en` list and the `NOS_IDIOMAS` variable from 0.3.3.
- The Voices tab shows each voice's language.
- The add-on reloads its Wyoming integration by itself after installing, uploading or deleting voices, and when the languages change.

## 0.3.3

- Voices also declare Spanish and English (they still speak Galician). Home Assistant's text-to-speech form (Media > Text-to-speech) only preselects a language that matches the system language; with Galician only, it showed no voice selector on Spanish or English installations. Override with the `NOS_IDIOMAS` environment variable (default `gl,es,en`).

## 0.3.2

- Engine selector (Torch / ONNX) for each voice in the Voices tab. It writes `<voice>.motor` to `ajustes.txt` and clears Home Assistant's TTS cache.

## 0.3.1

- Experimental ONNX engine: `motor = onnx` (per voice or global) in `ajustes.txt`. About twice as fast on a Raspberry Pi 5 (welcome sentence: 3.5 s instead of 7 s). The voice is exported to `<voice>.onnx` on first use. VITS noise is fed from outside the graph and generated with the seed, so the same sentence still gives the same audio. If ONNX fails, the add-on falls back to torch.
- Synthesis time is logged for each utterance.

## 0.3.0

- The Voces Nós page is available in Galician, Spanish and English. It follows Home Assistant's language (or the browser's) and has a language selector; the choice is remembered.
- The server sends error and progress messages as codes, translated by the page.
- Catalogue voices are described in the chosen language (Celtia: muller / mujer / female).
- Documentation (README and DOCS) in English, Galician and Spanish.

## 0.2.1

- Tabs in the page (Voices, Install, Try, Pronunciation & settings).
- "Make default" button to choose the default voice (stored as `defecto = name` in `ajustes.txt`).
- Saving the dictionary, the settings or the default voice clears Home Assistant's TTS cache (`homeassistant_api`).
- Own icon and logo.

## 0.2.0

- "Voces Nós" page in the sidebar (ingress): install voices from Hugging Face (with a token for gated models), upload your own models, try them, download the audio, delete voices and edit `pronuncia.txt` and `ajustes.txt`.
- Voices are detected by folder (any `<name>/` with a `.pth` and `config.json`) and loaded or unloaded without restarting.
- The add-on starts even with no voices installed.
- `/share` is mounted read-write.

## 0.1.0

- Wyoming TTS server with the Celtia and Brais voices (Coqui VITS, graphemes).
- Numbers to Galician words and removal of characters outside the vocabulary.
- Pronunciation dictionary (`/share/nos_tts/pronuncia.txt`).
- Per-voice settings: noise, duration noise, speed and seed (`/share/nos_tts/ajustes.txt`).
- Lower noise (0.5 / 0.3) and a fixed seed: stable, reproducible speech.
- Lowercase text for voices without `text_cleaner` (Brais).
