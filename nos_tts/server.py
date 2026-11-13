"""Servidor Wyoming TTS con las voces gallegas del Proxecto Nós (Coqui VITS, grafemas).

Cada voz es una carpeta <models>/<voz>/ con un .pth y su config.json.
Incluye una página web (ingress de Home Assistant) para descargar, subir, probar y borrar voces,
y para editar el diccionario de pronuncia y los ajustes.
Sin Cotovía: se normalizan los números (0-999 999) y se quitan caracteres desconocidos.
"""
import argparse
import asyncio
import gc
import io
import json
import logging
import os
import re
import shutil
import time
import wave

import numpy as np
import torch
from aiohttp import ClientSession, ClientTimeout, web
from TTS.utils.synthesizer import Synthesizer
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.error import Error
from wyoming.event import Event
from wyoming.info import Attribution, Describe, Info, TtsProgram, TtsVoice
from wyoming.server import AsyncEventHandler, AsyncServer
from wyoming.tts import Synthesize

VERSION = "0.4.3"
_LOG = logging.getLogger("nos_tts")
SIN_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate"}
# Idiomas que se declaran a Home Assistant: los de cada voz (`idioma` en su voz.json; "gl" si no
# lo dice) y, salvo `idioma_ha = no` en ajustes.txt, también el idioma del sistema de HA. Motivo:
# el formulario de Medios > Texto a voz solo preselecciona un idioma que coincida con el del
# sistema; si no hay ninguno, oculta el selector de voces. El audio no cambia.
IDIOMA_VOZ_DEFECTO = "gl"
ATRIB = Attribution(name="Proxecto Nós", url="https://huggingface.co/proxectonos")
WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

# Voces conocidas, para instalarlas con un clic desde la página web.
CATALOGO = [
    {"nombre": "celtia", "repo": "proxectonos/Nos_TTS-celtia-vits-graphemes",
     "descripcion": "Celtia (muller)", "genero": "f", "restringido": True},
    {"nombre": "brais", "repo": "proxectonos/Nos_TTS-brais-vits-graphemes",
     "descripcion": "Brais (home)", "genero": "m", "restringido": False},
]


class Fallo(RuntimeError):
    """Error con código traducible: la página lo muestra en el idioma elegido (web/app.html, I18N.e)."""

    TEXTOS = {  # en inglés, para los registros y para Wyoming
        "sin_voces": "No voice installed",
        "token_no_valido": "Invalid token",
        "repo_no_encontrado": "Repository {repo} not found ({status})",
        "repo_sin_modelo": "The repository has no .pth model and config.json",
        "restringido": "Gated model: accept its conditions on Hugging Face and use a read token from that account",
        "error_descarga": "Error {status} downloading {archivo}",
        "sin_espacio": "Not enough space in /share",
        "no_carga": "Saved, but the model does not load: {detalle}",
        "repo_no_valido": "Invalid repository or name",
        "instalando_ya": "{nombre} is already being installed",
        "nombre_no_valido": "Invalid name",
        "falta_nombre": "The name must come before the files",
        "faltan_archivos": "Both the model (.pth) and its config.json are needed",
        "voz_no_existe": "That voice does not exist",
        "voz_no_activa": "That voice is not active",
        "motor_no_valido": "Unknown engine (use torch or onnx)",
        "texto_vacio": "Write some text",
        "solo_ha": "Only reachable through Home Assistant",
    }

    def __init__(self, codigo: str, **p):
        self.codigo, self.p = codigo, p
        super().__init__(self.TEXTOS.get(codigo, codigo).format(**p))

    def json(self) -> dict:
        return {"c": self.codigo, "p": self.p}


def http_fallo(clase, codigo: str, **p):
    """Excepción HTTP con cuerpo JSON {"error": {"c": código, "p": parámetros}}."""
    return clase(text=json.dumps({"error": Fallo(codigo, **p).json()}), content_type="application/json")

UNIDADES = ["cero", "un", "dous", "tres", "catro", "cinco", "seis", "sete", "oito", "nove",
            "dez", "once", "doce", "trece", "catorce", "quince", "dezaseis", "dezasete",
            "dezaoito", "dezanove"]
DECENAS = {2: "vinte", 3: "trinta", 4: "corenta", 5: "cincuenta", 6: "sesenta",
           7: "setenta", 8: "oitenta", 9: "noventa"}
CENTENAS = {1: "cento", 2: "douscentos", 3: "trescentos", 4: "catrocentos", 5: "quiñentos",
            6: "seiscentos", 7: "setecentos", 8: "oitocentos", 9: "novecentos"}


def _menor_mil(n: int) -> str:
    if n < 20:
        return UNIDADES[n]
    if n < 100:
        d, u = divmod(n, 10)
        return DECENAS[d] + (f" e {UNIDADES[u]}" if u else "")
    if n == 100:
        return "cen"
    c, r = divmod(n, 100)
    return CENTENAS[c] + (f" {_menor_mil(r)}" if r else "")


def numero_a_texto(n: int) -> str:
    if n < 1000:
        return _menor_mil(n)
    m, r = divmod(n, 1000)
    pre = "mil" if m == 1 else f"{_menor_mil(m)} mil"
    return pre + (f" {_menor_mil(r)}" if r else "")


def normalizar(texto: str, vocab: str) -> str:
    def num(mt):
        s = mt.group(0)
        if len(s) > 6:  # números largos (teléfonos, códigos): cifra a cifra
            return " ".join(UNIDADES[int(c)] for c in s)
        return numero_a_texto(int(s))

    texto = re.sub(r"\d+", num, texto)
    texto = "".join(c for c in texto if c in vocab)
    return re.sub(r"\s+", " ", texto).strip()


def sanear(nombre: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "", (nombre or "").strip().lower())[:32]


class ArchivoReglas:
    """Archivo de texto `clave = valor` que se relee cuando cambia."""

    def __init__(self, ruta: str):
        self.ruta, self.mtime, self.reglas = ruta, None, {}

    def leer(self) -> dict:
        try:
            mtime = os.path.getmtime(self.ruta)
        except OSError:
            mtime = None
        if mtime != self.mtime:
            reglas = {}
            if mtime is not None:
                with open(self.ruta, encoding="utf-8") as f:
                    for linea in f:
                        linea = linea.split("#", 1)[0].strip()
                        if "=" in linea:
                            k, v = (x.strip() for x in linea.split("=", 1))
                            if k:
                                reglas[k.lower()] = v
            self.mtime, self.reglas = mtime, reglas
            self.cambiado()
        return self.reglas

    def cambiado(self):
        pass


class Diccionario(ArchivoReglas):
    """pronuncia.txt: `palabra = como_se_le`. Palabras completas, sin distinguir mayúsculas."""

    regex = None

    def cambiado(self):
        claves = sorted(self.reglas, key=len, reverse=True)
        self.regex = re.compile(r"\b(" + "|".join(map(re.escape, claves)) + r")\b", re.I) if claves else None
        _LOG.info("Diccionario de pronuncia: %d entradas", len(self.reglas))

    def aplicar(self, texto: str) -> str:
        reglas = self.leer()
        if not self.regex:
            return texto
        return self.regex.sub(lambda m: reglas[m.group(0).lower()], texto)


# VITS es aleatorio: con el ruido por defecto (0.667 / 1.0) a veces se come sonidos
# ("Bebidos" por "Benvidos"). Menos ruido = locución más estable.
AJUSTES_DEFECTO = {"ruido": 0.5, "ruido_duracion": 0.3, "velocidad": 1.0, "semilla": 1234, "motor": "torch"}


class Ajustes(ArchivoReglas):
    """ajustes.txt: `voz.clave = valor` o `clave = valor` (todas las voces)."""

    def para(self, voz: str) -> dict:
        reglas = self.leer()
        r = dict(AJUSTES_DEFECTO)
        for k in AJUSTES_DEFECTO:
            for clave in (k, f"{voz}.{k}"):
                if clave in reglas:
                    try:
                        v = reglas[clave]
                        r[k] = v.strip().lower() if isinstance(AJUSTES_DEFECTO[k], str) else float(v)
                    except ValueError:
                        _LOG.warning("Ajuste no válido: %s = %s", clave, reglas[clave])
        return r


def archivos_voz(carpeta: str):
    """(pth, config) de una carpeta de voz, o None si falta alguno."""
    try:
        nombres = os.listdir(carpeta)
    except OSError:
        return None
    pth = sorted(n for n in nombres if n.endswith(".pth"))
    cfg = "config.json" if "config.json" in nombres else next(
        (n for n in sorted(nombres) if n.endswith(".json") and "config" in n), None)
    if not pth or not cfg:
        return None
    return os.path.join(carpeta, pth[0]), os.path.join(carpeta, cfg)


def leer_meta(carpeta: str) -> dict:
    try:
        with open(os.path.join(carpeta, "voz.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def idioma_de(meta: dict, conocida: dict) -> str:
    """Idioma de una voz: el de su voz.json, el del catálogo o gallego."""
    i = str(meta.get("idioma") or conocida.get("idioma") or IDIOMA_VOZ_DEFECTO).strip().replace("-", "_")
    return i or IDIOMA_VOZ_DEFECTO


class Voz:
    def __init__(self, nombre: str, carpeta: str):
        self.nombre = nombre
        self.carpeta = carpeta
        self._sesion = None  # sesión ONNX (motor = onnx), se crea al primer uso
        pth, cfg = archivos_voz(carpeta)
        self.pth = pth
        meta = leer_meta(carpeta)
        conocida = next((c for c in CATALOGO if c["nombre"] == nombre), {})
        self.descripcion = meta.get("descripcion") or conocida.get("descripcion") or nombre
        self.idioma = idioma_de(meta, conocida)
        self.synth =Synthesizer(tts_checkpoint=pth, tts_config_path=cfg, use_cuda=False)
        # Brais trae `text_cleaner: null` (no pasa a minúsculas) y con mayúsculas se come la
        # primera consonante ("entro" por "Centro"). Celtia ya usa multilingual_cleaners.
        self.minusculas = not getattr(self.synth.tts_config, "text_cleaner", None)
        cfg_chars = self.synth.tts_config.characters
        self.vocab = cfg_chars.characters + cfg_chars.punctuations
        self.rate = self.synth.output_sample_rate

    # ---------- Motor ONNX (experimental; ajuste `motor = onnx`) ----------
    # Unas 2 veces más rápido que torch en una Pi 5. El ruido de VITS va dentro del grafo
    # (RandomNormalLike), donde torch.manual_seed no llega y onnxruntime no se puede reiniciar sin
    # recrear la sesión (2,4 s). Por eso esos nodos se sustituyen por una entrada `ruido_k`
    # recortada a la forma que haga falta: el ruido se genera aquí con la semilla y la misma frase
    # da siempre el mismo audio con una única sesión.
    RUIDO_FORMA = (1, 256, 16384)  # canales (z: 192, duración: 2) x longitud máxima (~3 min de audio)

    def _sesion_onnx(self):
        if getattr(self, "_sesion", None) is not None:
            return self._sesion
        import onnx
        import onnxruntime as ort
        from onnx import TensorProto, helper

        ruta = os.path.splitext(self.pth)[0] + ".onnx"
        if not os.path.exists(ruta) or os.path.getmtime(ruta) < os.path.getmtime(self.pth):
            _LOG.info("Exportando %s a ONNX…", self.nombre)
            t0 = time.time()
            tmp = ruta + ".tmp"
            self.synth.tts_model.export_onnx(output_path=tmp, verbose=False)
            os.replace(tmp, ruta)
            _LOG.info("Exportado %s (%.0f MB) en %.0f s", ruta, os.path.getsize(ruta) / 1e6, time.time() - t0)
        modelo = onnx.load(ruta)
        g = modelo.graph
        nodos, self._ruidos = [], []
        for nodo in g.node:
            if nodo.op_type not in ("RandomNormalLike", "RandomUniformLike"):
                if nodo.op_type.startswith("Random"):
                    raise RuntimeError(f"Nodo aleatorio no soportado: {nodo.op_type}")
                nodos.append(nodo)
                continue
            k = len(self._ruidos)
            attrs = {a.name: helper.get_attribute_value(a) for a in nodo.attribute}
            normal = nodo.op_type == "RandomNormalLike"
            self._ruidos.append(normal)
            nombre = f"ruido_{k}"
            g.input.append(helper.make_tensor_value_info(nombre, TensorProto.FLOAT, ["r0", "r1", "r2"]))
            g.initializer.append(helper.make_tensor(f"{nombre}_ini", TensorProto.INT64, [3], [0, 0, 0]))
            nodos += [
                helper.make_node("Shape", [nodo.input[0]], [f"{nombre}_forma"]),
                helper.make_node("Slice", [nombre, f"{nombre}_ini", f"{nombre}_forma"], [f"{nombre}_r"]),
            ]
            # Normal: media + escala * N(0,1). Uniforme: bajo + (alto - bajo) * U(0,1).
            mul = attrs.get("scale", 1.0) if normal else attrs.get("high", 1.0) - attrs.get("low", 0.0)
            suma = attrs.get("mean", 0.0) if normal else attrs.get("low", 0.0)
            g.initializer.append(helper.make_tensor(f"{nombre}_mul", TensorProto.FLOAT, [], [mul]))
            g.initializer.append(helper.make_tensor(f"{nombre}_suma", TensorProto.FLOAT, [], [suma]))
            nodos += [
                helper.make_node("Mul", [f"{nombre}_r", f"{nombre}_mul"], [f"{nombre}_m"]),
                helper.make_node("Add", [f"{nombre}_m", f"{nombre}_suma"], [nodo.output[0]]),
            ]
        del g.node[:]
        g.node.extend(nodos)
        op = ort.SessionOptions()
        op.intra_op_num_threads = torch.get_num_threads()
        t0 = time.time()
        self._sesion = ort.InferenceSession(modelo.SerializeToString(), sess_options=op,
                                            providers=["CPUExecutionProvider"])
        _LOG.info("ONNX %s: %d nodos aleatorios sustituidos; sesión creada en %.1f s",
                  self.nombre, len(self._ruidos), time.time() - t0)
        return self._sesion

    def _ruido(self, semilla: int) -> dict:
        if getattr(self, "_ruido_semilla", None) != semilla:
            rng = np.random.default_rng(semilla)
            self._ruido_cache = {
                f"ruido_{k}": (rng.standard_normal(self.RUIDO_FORMA, dtype=np.float32) if normal
                               else rng.random(self.RUIDO_FORMA, dtype=np.float32))
                for k, normal in enumerate(self._ruidos)}
            self._ruido_semilla = semilla
        return self._ruido_cache

    def sintetizar_onnx(self, texto: str, aj: dict) -> np.ndarray:
        sesion = self._sesion_onnx()
        ruido = self._ruido(int(aj["semilla"]))
        m = self.synth.tts_model
        idioma = m.language_manager.language_names[0] if m.language_manager.num_languages == 1 else None
        escalas = np.array([aj["ruido"], 1.0 / max(aj["velocidad"], 0.1), aj["ruido_duracion"]], dtype=np.float32)
        trozos = []
        for frase in self.synth.split_into_sentences(texto):
            ids = np.asarray(m.tokenizer.text_to_ids(frase, language=idioma), dtype=np.int64)[None, :]
            sal = sesion.run(["output"], {"input": ids, "input_lengths": np.array([ids.shape[1]], dtype=np.int64),
                                          "scales": escalas, **ruido})[0]
            wav = np.asarray(sal, dtype=np.float32).reshape(-1)
            if self.synth.tts_config.audio.get("do_trim_silence"):
                wav = wav[: m.ap.find_endpoint(wav)]
            trozos += [wav, np.zeros(10000, dtype=np.float32)]  # mismo silencio que Synthesizer.tts
        return np.concatenate(trozos[:-1]) if trozos else np.zeros(0, dtype=np.float32)


class Estado:
    def __init__(self, carpeta: str):
        self.carpeta = carpeta
        self.voces: dict[str, Voz] = {}
        self.errores: dict[str, str] = {}
        self.lock = asyncio.Lock()
        self.dicc = Diccionario(os.path.join(carpeta, "pronuncia.txt"))
        self.ajustes = Ajustes(os.path.join(carpeta, "ajustes.txt"))
        self.tareas: dict[str, dict] = {}
        self.idioma_sistema = None  # idioma de Home Assistant (p. ej. "es"); se lee de la API de Core

    @property
    def idioma_ha(self) -> bool:
        """¿Declarar también el idioma de HA? (ajuste global `idioma_ha`, por defecto sí)."""
        return self.ajustes.leer().get("idioma_ha", "si").strip().lower() not in ("no", "0", "false", "off")

    def idiomas(self, voz: "Voz") -> list[str]:
        r = [voz.idioma]
        extra = self.idioma_sistema
        if self.idioma_ha and extra and extra.split("_")[0].split("-")[0] != voz.idioma.split("_")[0]:
            r.append(extra)
        return r

    @property
    def defecto(self):
        elegida = self.ajustes.leer().get("defecto")
        if elegida in self.voces:
            return elegida
        if "celtia" in self.voces:
            return "celtia"
        return min(self.voces) if self.voces else None

    def fijar_ajuste(self, clave: str, valor: str):
        """Escribe `clave = valor` en ajustes.txt, quitando la línea anterior de esa clave y conservando el resto."""
        ruta = os.path.join(self.carpeta, "ajustes.txt")
        try:
            with open(ruta, encoding="utf-8") as f:
                lineas = f.read().splitlines()
        except OSError:
            lineas = []
        patron = re.compile(r"\s*" + re.escape(clave) + r"\s*=", re.I)
        lineas = [l for l in lineas if not patron.match(l)]
        lineas.append(f"{clave} = {valor}")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas) + "\n")

    def fijar_defecto(self, nombre: str):
        self.fijar_ajuste("defecto", nombre)

    def motor(self, nombre: str) -> str:
        return "onnx" if self.ajustes.para(nombre)["motor"] == "onnx" else "torch"

    def carpetas(self):
        try:
            nombres = sorted(os.listdir(self.carpeta))
        except OSError:
            return []
        return [n for n in nombres
                if not n.startswith(".") and os.path.isdir(os.path.join(self.carpeta, n))
                and archivos_voz(os.path.join(self.carpeta, n))]

    async def cargar(self, nombre: str):
        _LOG.info("Cargando %s…", nombre)
        self.descargar_de_memoria(nombre)
        loop = asyncio.get_running_loop()
        try:
            async with self.lock:
                self.voces[nombre] = await loop.run_in_executor(
                    None, Voz, nombre, os.path.join(self.carpeta, nombre))
            self.errores.pop(nombre, None)
        except Exception as e:  # modelo roto o incompatible
            _LOG.exception("No se pudo cargar %s", nombre)
            self.errores[nombre] = str(e)

    def descargar_de_memoria(self, nombre: str):
        if self.voces.pop(nombre, None) is not None:
            gc.collect()

    async def cargar_todas(self):
        for nombre in list(self.voces):
            if nombre not in self.carpetas():
                self.descargar_de_memoria(nombre)
        for nombre in self.carpetas():
            await self.cargar(nombre)
        _LOG.info("Listo. Voces: %s (por defecto %s)", ", ".join(self.voces) or "ninguna", self.defecto)

    def info(self) -> Info:
        return Info(tts=[TtsProgram(
            name="nos_tts", description="Nós TTS (gallego)", attribution=ATRIB,
            installed=True, version=VERSION,
            voices=[TtsVoice(name=n, description=v.descripcion, attribution=ATRIB,
                             installed=True, version=None, languages=self.idiomas(v))
                    for n, v in sorted(self.voces.items())],
        )])

    async def sintetizar(self, nombre, texto):
        nombre = nombre if nombre in self.voces else self.defecto
        if not nombre:
            raise Fallo("sin_voces")
        voz = self.voces[nombre]
        texto = normalizar(self.dicc.aplicar(texto), voz.vocab)
        if voz.minusculas:
            texto = texto.lower()
        aj = self.ajustes.para(voz.nombre)
        _LOG.info("Sintetizando con %s %s: %s", voz.nombre, aj, texto)
        loop = asyncio.get_running_loop()
        async with self.lock:
            m = voz.synth.tts_model
            m.inference_noise_scale = aj["ruido"]
            m.inference_noise_scale_dp = aj["ruido_duracion"]
            m.length_scale = 1.0 / max(aj["velocidad"], 0.1)
            torch.manual_seed(int(aj["semilla"]))  # misma frase -> mismo audio
            t0 = time.time()
            wav = None
            if aj["motor"] == "onnx":
                try:
                    wav = await loop.run_in_executor(None, voz.sintetizar_onnx, texto, aj)
                except Exception:
                    _LOG.exception("ONNX falló con %s; se usa torch", voz.nombre)
                    aj["motor"] = "torch (ONNX falló)"
            if wav is None:
                wav = await loop.run_in_executor(None, voz.synth.tts, texto)
            _LOG.info("Sintetizado con %s en %.2f s (%.1f s de audio)", aj["motor"], time.time() - t0,
                      len(wav) / voz.rate)
        pcm = (np.clip(np.asarray(wav, dtype=np.float32), -1, 1) * 32767).astype("<i2").tobytes()
        return pcm, voz.rate


class Handler(AsyncEventHandler):
    def __init__(self, estado, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.estado = estado

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self.estado.info().event())
            return True
        if not Synthesize.is_type(event.type):
            return True
        syn = Synthesize.from_event(event)
        nombre = syn.voice.name if (syn.voice and syn.voice.name) else None
        try:
            pcm, rate = await self.estado.sintetizar(nombre, syn.text)
        except Exception as e:
            _LOG.exception("Error al sintetizar")
            await self.write_event(Error(text=str(e), code="nos_tts").event())
            return True
        await self.write_event(AudioStart(rate=rate, width=2, channels=1).event())
        paso = 4096
        for i in range(0, len(pcm), paso):
            await self.write_event(AudioChunk(rate=rate, width=2, channels=1, audio=pcm[i:i + paso]).event())
        await self.write_event(AudioStop().event())
        return True


# ---------------------------------------------------------------- página web (ingress)

PERMITIDAS = {"172.30.32.2", "127.0.0.1", "::1"}  # 172.30.32.2 = proxy de ingress del Supervisor
TEXTOS = {"pronuncia": "pronuncia.txt", "ajustes": "ajustes.txt"}


@web.middleware
async def solo_ingress(request, handler):
    if request.remote not in PERMITIDAS:
        raise http_fallo(web.HTTPForbidden, "solo_ha")
    return await handler(request)


def tamano(carpeta):
    total = 0
    for raiz, _, nombres in os.walk(carpeta):
        for n in nombres:
            try:
                total += os.path.getsize(os.path.join(raiz, n))
            except OSError:
                pass
    return total


def rutas(estado: Estado) -> web.RouteTableDef:
    r = web.RouteTableDef()

    @r.get("/")
    async def inicio(_):
        # index.html es solo un cargador que pide app.html por JavaScript (ver el comentario allí).
        # Ambos van sin caché: tras actualizar el complemento, se ve siempre la página nueva.
        return web.FileResponse(os.path.join(WEB, "index.html"), headers=SIN_CACHE)

    @r.get("/app.html")
    async def app_html(_):
        return web.FileResponse(os.path.join(WEB, "app.html"), headers=SIN_CACHE)

    @r.get("/api/estado")
    async def api_estado(request):
        voces = []
        if "X-Nos-Web" not in request.headers:
            # Página antigua (≤ 0.4.1) guardada en la caché del navegador para el iframe de HA: no
            # tiene el cargador de 0.4.2, pero sí pide estos datos y pinta sin escapar el motor de
            # las voces sin cargar. Esta fila falsa lleva una imagen rota cuyo onerror navega el
            # iframe a app.html (URL nueva, sin caché). Las páginas actuales envían X-Nos-Web y no
            # la reciben. Quitar cuando ya no queden copias viejas.
            voces.append({
                "nombre": "…", "descripcion": "", "repo": None, "tamano": 0, "cargada": False,
                "error": None, "defecto": False, "onnx_listo": False,
                "motor": "<img src=\"nos-recargar.png\" alt=\"\" style=\"display:none\" "
                         "onerror=\"if(!window.__nosRecargar){window.__nosRecargar=1;"
                         "location.replace('app.html?v=" + VERSION + "-'+Date.now()+location.hash)}\">",
            })
        for n in estado.carpetas():
            carpeta = os.path.join(estado.carpeta, n)
            v = estado.voces.get(n)
            meta = leer_meta(carpeta)
            voces.append({
                "nombre": n, "descripcion": v.descripcion if v else (meta.get("descripcion") or n),
                "repo": meta.get("repo"), "tamano": tamano(carpeta), "cargada": v is not None,
                "error": estado.errores.get(n), "defecto": n == estado.defecto,
                "motor": estado.motor(n),
                "onnx_listo": os.path.exists(os.path.join(carpeta, n + ".onnx")),
                "idioma": v.idioma if v else idioma_de(meta, {}),
                "idiomas": estado.idiomas(v) if v else [],
            })
        ocupado = {t["nombre"] for t in estado.tareas.values() if t["estado"] == "en curso"}
        return web.json_response({
            "version": VERSION, "voces": voces, "catalogo": CATALOGO,
            "idioma_ha": estado.idioma_ha, "idioma_sistema": estado.idioma_sistema,
            "tareas": sorted(estado.tareas.values(), key=lambda t: -t["inicio"])[:10],
            "ocupado": sorted(ocupado), "libre": shutil.disk_usage(estado.carpeta).free,
        })

    @r.post("/api/descargar")
    async def api_descargar(request):
        d = await request.json()
        repo = (d.get("repo") or "").strip()
        nombre = sanear(d.get("nombre") or repo.split("/")[-1].replace("Nos_TTS-", "").split("-")[0])
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo) or not nombre:
            raise http_fallo(web.HTTPBadRequest, "repo_no_valido")
        if any(t["nombre"] == nombre and t["estado"] == "en curso" for t in estado.tareas.values()):
            raise http_fallo(web.HTTPConflict, "instalando_ya", nombre=nombre)
        tid = f"{nombre}-{int(time.time())}"
        estado.tareas[tid] = {"id": tid, "nombre": nombre, "repo": repo, "estado": "en curso",
                              "msg": {"c": "empezando"}, "hecho": 0, "total": 0, "inicio": time.time()}
        token = (d.get("token") or "").strip() or None  # solo para esta descarga; no se guarda
        desc = d.get("descripcion") or next((c["descripcion"] for c in CATALOGO if c["repo"] == repo), None)
        asyncio.create_task(descargar(estado, estado.tareas[tid], repo, nombre, token, desc))
        return web.json_response({"id": tid})

    @r.post("/api/subir")
    async def api_subir(request):
        reader = await request.multipart()
        nombre, desc, tmp, recibidos = None, None, None, set()
        try:
            while (parte := await reader.next()) is not None:
                if parte.name == "nombre":
                    nombre = sanear(await parte.text())
                    if not nombre:
                        raise http_fallo(web.HTTPBadRequest, "nombre_no_valido")
                    tmp = os.path.join(estado.carpeta, f".{nombre}.subida")
                    shutil.rmtree(tmp, ignore_errors=True)
                    os.makedirs(tmp)
                elif parte.name == "descripcion":
                    desc = (await parte.text()).strip()[:80]
                elif parte.name in ("modelo", "config"):
                    if not tmp:
                        raise http_fallo(web.HTTPBadRequest, "falta_nombre")
                    destino = f"{nombre}.pth" if parte.name == "modelo" else "config.json"
                    with open(os.path.join(tmp, destino), "wb") as f:
                        while chunk := await parte.read_chunk(1 << 20):
                            f.write(chunk)
                    recibidos.add(parte.name)
            if recibidos != {"modelo", "config"}:
                raise http_fallo(web.HTTPBadRequest, "faltan_archivos")
            with open(os.path.join(tmp, "voz.json"), "w", encoding="utf-8") as f:
                json.dump({"descripcion": desc or nombre, "origen": "subida"}, f, ensure_ascii=False)
            final = os.path.join(estado.carpeta, nombre)
            shutil.rmtree(final, ignore_errors=True)
            os.rename(tmp, final)
            tmp = None
        finally:
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)
        await estado.cargar(nombre)
        if nombre in estado.errores:
            raise http_fallo(web.HTTPBadRequest, "no_carga", detalle=estado.errores[nombre])
        return web.json_response({"ok": True, "nombre": nombre, "wyoming_recargado": await recargar_wyoming()})

    @r.delete("/api/voces/{nombre}")
    async def api_borrar(request):
        nombre = sanear(request.match_info["nombre"])
        carpeta = os.path.join(estado.carpeta, nombre)
        if not nombre or not os.path.isdir(carpeta):
            raise http_fallo(web.HTTPNotFound, "voz_no_existe")
        async with estado.lock:
            estado.descargar_de_memoria(nombre)
        shutil.rmtree(carpeta)
        estado.errores.pop(nombre, None)
        return web.json_response({"ok": True, "wyoming_recargado": await recargar_wyoming()})

    @r.post("/api/recargar")
    async def api_recargar(_):
        await estado.cargar_todas()
        return web.json_response({"voces": sorted(estado.voces), "wyoming_recargado": await recargar_wyoming()})

    @r.get("/api/texto/{cual}")
    async def api_leer_texto(request):
        cual = request.match_info["cual"]
        if cual not in TEXTOS:
            raise web.HTTPNotFound()
        try:
            with open(os.path.join(estado.carpeta, TEXTOS[cual]), encoding="utf-8") as f:
                return web.Response(text=f.read())
        except OSError:
            return web.Response(text="")

    @r.put("/api/texto/{cual}")
    async def api_guardar_texto(request):
        cual = request.match_info["cual"]
        if cual not in TEXTOS:
            raise web.HTTPNotFound()
        texto = await request.text()
        if len(texto) > 200_000:
            raise web.HTTPRequestEntityTooLarge(max_size=200_000, actual_size=len(texto))
        with open(os.path.join(estado.carpeta, TEXTOS[cual]), "w", encoding="utf-8") as f:
            f.write(texto)
        return web.json_response({"ok": True, "cache_vaciada": await vaciar_cache_ha()})

    @r.post("/api/defecto")
    async def api_defecto(request):
        nombre = sanear((await request.json()).get("nombre"))
        if nombre not in estado.voces:
            raise http_fallo(web.HTTPBadRequest, "voz_no_activa")
        estado.fijar_defecto(nombre)
        return web.json_response({"ok": True, "defecto": estado.defecto, "cache_vaciada": await vaciar_cache_ha()})

    @r.post("/api/motor")
    async def api_motor(request):
        datos = await request.json()
        nombre, motor = sanear(datos.get("nombre")), str(datos.get("motor") or "").lower()
        if nombre not in estado.voces:
            raise http_fallo(web.HTTPBadRequest, "voz_no_activa")
        if motor not in ("torch", "onnx"):
            raise http_fallo(web.HTTPBadRequest, "motor_no_valido")
        estado.fijar_ajuste(f"{nombre}.motor", motor)
        return web.json_response({"ok": True, "motor": estado.motor(nombre), "cache_vaciada": await vaciar_cache_ha()})

    @r.post("/api/idioma_ha")
    async def api_idioma_ha(request):
        activo = bool((await request.json()).get("activo"))
        estado.fijar_ajuste("idioma_ha", "si" if activo else "no")
        return web.json_response({"ok": True, "idioma_ha": estado.idioma_ha,
                                  "wyoming_recargado": await recargar_wyoming()})

    @r.post("/api/probar")
    async def api_probar(request):
        d = await request.json()
        texto = (d.get("texto") or "").strip()[:1000]
        if not texto:
            raise http_fallo(web.HTTPBadRequest, "texto_vacio")
        try:
            pcm, rate = await estado.sintetizar(d.get("voz"), texto)
        except Fallo as e:
            raise http_fallo(web.HTTPBadRequest, e.codigo, **e.p)
        except RuntimeError as e:
            raise web.HTTPBadRequest(text=str(e))
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(pcm)
        return web.Response(body=buf.getvalue(), content_type="audio/wav")

    return r


async def api_core(metodo: str, ruta: str, datos=None):
    """Llama a la API REST de Home Assistant (homeassistant_api). Devuelve el JSON o None."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return None
    try:
        async with ClientSession(timeout=ClientTimeout(total=15)) as s:
            async with s.request(metodo, "http://supervisor/core/api" + ruta, json=datos,
                                 headers={"Authorization": f"Bearer {token}"}) as r:
                if r.status != 200:
                    _LOG.warning("API de HA %s %s: HTTP %s", metodo, ruta, r.status)
                    return None
                return await r.json(content_type=None)
    except Exception as e:
        _LOG.warning("API de HA %s %s: %s", metodo, ruta, e)
        return None


async def vaciar_cache_ha() -> bool:
    """Vacía la caché de TTS de Home Assistant (tts.clear_cache) para oír los cambios al momento."""
    return await api_core("POST", "/services/tts/clear_cache", {}) is not None


async def recargar_wyoming() -> bool:
    """Recarga la entrada Wyoming de este complemento (título "nos_tts") para que HA vea los
    cambios de voces o idiomas sin tocar nada a mano."""
    entradas = await api_core("GET", "/config/config_entries/entry?domain=wyoming") or []
    ok = False
    for e in entradas:
        if e.get("title") == "nos_tts":
            ok = await api_core("POST", f"/config/config_entries/entry/{e['entry_id']}/reload") is not None or ok
    return ok


async def vigilar_idioma_ha(estado: Estado):
    """Lee el idioma del sistema de HA al arrancar y cada 10 min; si cambia, recarga Wyoming."""
    await asyncio.sleep(5)  # que el servidor Wyoming ya esté escuchando cuando HA recargue
    while True:
        cfg = await api_core("GET", "/config")
        idioma = (cfg or {}).get("language")
        if idioma and idioma != estado.idioma_sistema:
            _LOG.info("Idioma de Home Assistant: %s", idioma)
            estado.idioma_sistema = idioma
            if estado.idioma_ha:
                await recargar_wyoming()
        await asyncio.sleep(600 if idioma else 30)


async def descargar(estado: Estado, tarea: dict, repo: str, nombre: str, token, desc):
    """Descarga <repo> de Hugging Face a <models>/<nombre>/ y carga la voz."""
    cab = {"Authorization": f"Bearer {token}"} if token else {}
    tmp = os.path.join(estado.carpeta, f".{nombre}.descarga")
    try:
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp)
        async with ClientSession(timeout=ClientTimeout(total=None, sock_connect=30, sock_read=120)) as s:
            tarea["msg"] = {"c": "consultando"}
            async with s.get(f"https://huggingface.co/api/models/{repo}", headers=cab) as r:
                if r.status == 401 and token:
                    raise Fallo("token_no_valido")
                if r.status != 200:
                    raise Fallo("repo_no_encontrado", repo=repo, status=r.status)
                meta = await r.json()
            archivos = [x["rfilename"] for x in meta.get("siblings", [])]
            pths = [f for f in archivos if f.endswith(".pth")]
            cfgs = [f for f in archivos if f.endswith(".json") and "config" in f.lower()]
            if not pths or not cfgs:
                raise Fallo("repo_sin_modelo")
            pth = next((f for f in pths if os.path.basename(f) == f"{nombre}.pth"), pths[0])
            cfg = "config.json" if "config.json" in cfgs else cfgs[0]
            for remoto, local in ((cfg, "config.json"), (pth, f"{nombre}.pth")):
                url = f"https://huggingface.co/{repo}/resolve/main/{remoto}"
                async with s.get(url, headers=cab) as r:
                    if r.status in (401, 403):
                        raise Fallo("restringido")
                    if r.status != 200:
                        raise Fallo("error_descarga", status=r.status, archivo=remoto)
                    tarea.update(msg={"c": "descargando", "p": {"archivo": remoto}}, hecho=0, total=int(r.headers.get("Content-Length") or 0))
                    if local.endswith(".pth") and tarea["total"] > shutil.disk_usage(estado.carpeta).free - (200 << 20):
                        raise Fallo("sin_espacio")
                    with open(os.path.join(tmp, local), "wb") as f:
                        async for chunk in r.content.iter_chunked(1 << 20):
                            f.write(chunk)
                            tarea["hecho"] += len(chunk)
        with open(os.path.join(tmp, "voz.json"), "w", encoding="utf-8") as f:
            json.dump({"descripcion": desc or nombre, "repo": repo, "archivo": pth}, f, ensure_ascii=False)
        final = os.path.join(estado.carpeta, nombre)
        async with estado.lock:
            estado.descargar_de_memoria(nombre)
        shutil.rmtree(final, ignore_errors=True)
        os.rename(tmp, final)
        tarea["msg"] = {"c": "cargando"}
        await estado.cargar(nombre)
        if nombre in estado.errores:
            raise Fallo("no_carga", detalle=estado.errores[nombre])
        tarea.update(estado="ok", msg={"c": "instalada"})
        await recargar_wyoming()
    except Exception as e:
        _LOG.warning("Descarga de %s fallida: %s", repo, e)
        tarea.update(estado="error", msg=e.json() if isinstance(e, Fallo) else {"c": "error", "p": {"detalle": str(e)}})
        shutil.rmtree(tmp, ignore_errors=True)


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--models", default="/share/nos_tts")
    p.add_argument("--port", type=int, default=10200)
    p.add_argument("--web-port", type=int, default=8099)
    a = p.parse_args()
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    torch.set_num_threads(4)
    os.makedirs(a.models, exist_ok=True)

    estado = Estado(a.models)
    await estado.cargar_todas()
    if not estado.voces:
        _LOG.warning("No hay voces: instálalas desde la página del complemento")

    tarea_idioma = asyncio.create_task(vigilar_idioma_ha(estado))  # noqa: F841 (referencia viva)

    app = web.Application(middlewares=[solo_ingress])
    app.add_routes(rutas(estado))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", a.web_port).start()
    _LOG.info("Página web en el puerto %d", a.web_port)

    server = AsyncServer.from_uri(f"tcp://0.0.0.0:{a.port}")
    await server.run(lambda *args, **kw: Handler(estado, *args, **kw))


if __name__ == "__main__":
    asyncio.run(main())
