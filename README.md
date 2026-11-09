# Laboratorio GitOps — Etapa 1

Objetivo: entender el mecanismo central de GitOps **sin instalar nada** (solo Python).

## La metáfora

En GitOps real tenemos 3 piezas. Aquí las simulamos así:

| Pieza real (GitOps)         | En este laboratorio                        |
|-----------------------------|--------------------------------------------|
| Repositorio Git (verdad)    | Archivo `estado_deseado.yaml`              |
| Cluster / infraestructura   | Archivo `estado_real.json` (lo que "corre")|
| Agente (Argo CD / Flux)     | Script `agente.py`                         |

## El ciclo de GitOps

1. Tú declaras lo que QUIERES en `estado_deseado.yaml` (como harías en Git).
2. El agente lee ese archivo (el estado deseado).
3. El agente mira el estado REAL (lo que de verdad está corriendo).
4. Compara ambos y calcula la diferencia (**diff**).
5. Aplica los cambios necesarios para que la realidad coincida (**reconciliación**).
6. Si alguien cambia la realidad a mano, el agente lo detecta (**drift**) y lo corrige.

## Cómo usarlo

```powershell
# 1. Ver el estado actual
python agente.py estado

# 2. Reconciliar: hacer que la realidad coincida con lo deseado
python agente.py sync
```

Edita `estado_deseado.yaml`, vuelve a correr `sync`, y observa cómo el agente aplica
solo las diferencias. Eso es GitOps.
