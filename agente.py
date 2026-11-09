"""
AGENTE GITOPS (simulado) - Etapa 1 del laboratorio
===================================================

Este script imita lo que hacen herramientas reales como Argo CD o Flux,
pero en pequenito y sin Kubernetes, para que entiendas el MECANISMO.

Las 3 piezas:
  - estado_deseado.yaml -> lo que TU quieres (hace de "repositorio Git")
  - estado_real.json    -> lo que de verdad "esta corriendo" (hace de "cluster")
  - este script         -> el agente que reconcilia ambos

Comandos:
  python agente.py estado   -> muestra deseado vs real y las diferencias
  python agente.py sync     -> reconcilia: cambia lo real para que iguale lo deseado
  python agente.py drift    -> provoca un cambio manual en lo real (para experimentar)
"""

import json
import os
import sys

# Rutas de los archivos (quedan junto a este script)
CARPETA = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_DESEADO = os.path.join(CARPETA, "estado_deseado.yaml")
ARCHIVO_REAL = os.path.join(CARPETA, "estado_real.json")


# ---------------------------------------------------------------------------
# 1) LEER EL ESTADO DESEADO (nuestro "repositorio Git")
# ---------------------------------------------------------------------------
def leer_estado_deseado():
    """
    Lee estado_deseado.yaml con un mini-parser propio.
    Soporta justo la estructura simple de nuestro archivo:

        aplicaciones:
          web:
            version: "1.0"
            replicas: 2

    (En el mundo real usarias la libreria pyyaml, pero aqui evitamos
    instalar dependencias para empezar lo mas simple posible.)
    """
    deseado = {}
    app_actual = None

    with open(ARCHIVO_DESEADO, "r", encoding="utf-8") as f:
        for linea in f:
            # Quitar comentarios y espacios en blanco al final
            sin_comentario = linea.split("#", 1)[0].rstrip()
            if not sin_comentario.strip():
                continue  # linea vacia, la saltamos

            # Contamos la indentacion (numero de espacios al inicio)
            indent = len(sin_comentario) - len(sin_comentario.lstrip())
            contenido = sin_comentario.strip()

            if contenido == "aplicaciones:":
                continue  # es la cabecera, no hace falta hacer nada
            elif indent == 2:
                # Nombre de una app, ej: "web:"
                app_actual = contenido.rstrip(":")
                deseado[app_actual] = {}
            elif indent == 4 and app_actual is not None:
                # Una propiedad de la app, ej: 'version: "1.0"'
                clave, valor = contenido.split(":", 1)
                valor = valor.strip().strip('"')
                # replicas es numero; el resto texto
                if clave.strip() == "replicas":
                    valor = int(valor)
                deseado[app_actual][clave.strip()] = valor

    return deseado


# ---------------------------------------------------------------------------
# 2) LEER / GUARDAR EL ESTADO REAL (nuestro "cluster")
# ---------------------------------------------------------------------------
def leer_estado_real():
    """Lee lo que esta 'corriendo'. Si no existe el archivo, empezamos vacios."""
    if not os.path.exists(ARCHIVO_REAL):
        return {}
    with open(ARCHIVO_REAL, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_estado_real(estado):
    """Persiste el estado real en disco (simula aplicar cambios al cluster)."""
    with open(ARCHIVO_REAL, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 3) CALCULAR LA DIFERENCIA (el "diff" que hace Argo CD)
# ---------------------------------------------------------------------------
def calcular_diferencias(deseado, real):
    """
    Devuelve una lista de acciones necesarias para que 'real' se parezca a 'deseado'.
    Cada accion es una frase descriptiva de lo que hay que hacer.
    """
    acciones = []

    # Apps que deberian existir
    for app, config in deseado.items():
        if app not in real:
            acciones.append(("CREAR", app, dict(config)))
        else:
            # La app existe: revisamos si alguna propiedad cambio
            for clave, valor in config.items():
                if real[app].get(clave) != valor:
                    acciones.append(("ACTUALIZAR", app, (clave, real[app].get(clave), valor)))

    # Apps que existen en la realidad pero YA NO estan en lo deseado -> borrar
    for app in real:
        if app not in deseado:
            acciones.append(("ELIMINAR", app, None))

    return acciones


# ---------------------------------------------------------------------------
# COMANDOS
# ---------------------------------------------------------------------------
def comando_estado():
    deseado = leer_estado_deseado()
    real = leer_estado_real()
    acciones = calcular_diferencias(deseado, real)

    print("\n=== ESTADO DESEADO (lo que pediste en el 'repo') ===")
    for app, cfg in deseado.items():
        print(f"  - {app}: version {cfg['version']}, {cfg['replicas']} replica(s)")

    print("\n=== ESTADO REAL (lo que esta corriendo) ===")
    if not real:
        print("  (nada esta corriendo todavia)")
    for app, cfg in real.items():
        print(f"  - {app}: version {cfg['version']}, {cfg['replicas']} replica(s)")

    print("\n=== DIFERENCIAS ===")
    if not acciones:
        print("  OK - Sincronizado. La realidad ya coincide con lo deseado.")
    else:
        for tipo, app, detalle in acciones:
            if tipo == "CREAR":
                print(f"  [+] CREAR '{app}' -> {detalle}")
            elif tipo == "ELIMINAR":
                print(f"  [-] ELIMINAR '{app}' (ya no esta en lo deseado)")
            elif tipo == "ACTUALIZAR":
                clave, antes, despues = detalle
                print(f"  [~] ACTUALIZAR '{app}': {clave} de '{antes}' a '{despues}'")
    print()


def comando_sync():
    deseado = leer_estado_deseado()
    real = leer_estado_real()
    acciones = calcular_diferencias(deseado, real)

    if not acciones:
        print("\nNada que hacer. Ya esta sincronizado.\n")
        return

    print("\n=== RECONCILIANDO (aplicando cambios) ===")
    for tipo, app, detalle in acciones:
        if tipo == "CREAR":
            real[app] = detalle
            print(f"  [+] Creada '{app}'")
        elif tipo == "ELIMINAR":
            del real[app]
            print(f"  [-] Eliminada '{app}'")
        elif tipo == "ACTUALIZAR":
            clave, antes, despues = detalle
            real[app][clave] = despues
            print(f"  [~] '{app}': {clave} -> '{despues}'")

    guardar_estado_real(real)
    print("\nListo. La realidad ahora coincide con lo deseado.\n")


def comando_drift():
    """
    Simula que alguien toco el cluster a mano (sin pasar por Git).
    Cambiamos la version de 'web' directamente en el estado real.
    Luego corre 'python agente.py estado' y veras el DRIFT detectado.
    """
    real = leer_estado_real()
    if "web" in real:
        real["web"]["version"] = "9.9-hecho-a-mano"
        guardar_estado_real(real)
        print("\nSe modifico 'web' a mano en el estado real (simulando un cambio manual).")
        print("Corre 'python agente.py estado' para ver el DRIFT, y 'sync' para corregirlo.\n")
    else:
        print("\nNo hay app 'web' corriendo. Corre primero 'python agente.py sync'.\n")


# ---------------------------------------------------------------------------
# PUNTO DE ENTRADA
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    comando = sys.argv[1] if len(sys.argv) > 1 else "estado"

    if comando == "estado":
        comando_estado()
    elif comando == "sync":
        comando_sync()
    elif comando == "drift":
        comando_drift()
    else:
        print(f"Comando desconocido: '{comando}'")
        print("Usa: estado | sync | drift")
