<div align="center">

# FileFlow CLI 📁

**Organiza archivos de forma segura. Previsualiza cada movimiento. Deshaz con confianza.**

[🇺🇸 English](README.md) · [🇧🇷 Português](README.pt-BR.md) · [🇪🇸 Español](README.es.md)

[![CI](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)
[![Python 3.14](https://img.shields.io/badge/Python-3.14-blue)](https://www.python.org/)
[![Typer](https://img.shields.io/badge/Typer-CLI-7c3aed)](https://typer.tiangolo.com/)
[![Rich](https://img.shields.io/badge/Rich-terminal-f59e0b)](https://github.com/Textualize/rich)
[![PyYAML](https://img.shields.io/badge/PyYAML-config-ef4444)](https://pyyaml.org/)

[![pytest](https://img.shields.io/badge/pytest-92%20tests%2Fplatform-0ea5e9)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/badge/Ruff-lint%20%2B%20format-111827)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)
[![Build](https://img.shields.io/badge/build-wheel%20verified-2563eb)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)
[![CLI smoke](https://img.shields.io/badge/CLI-smoke%20tested-14b8a6)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)
[![MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

</div>

> **Estado:** desarrollo finalizado, revisión final de Codex completada y código integrado en `main`. GitHub Actions aprobado en Windows, Ubuntu y macOS (92 pruebas por plataforma). El paquete aún no se ha publicado en PyPI.

## Objetivo y funciones

FileFlow es una herramienta de automatización real en Python y un ejemplo de diseño modular, seguridad explícita y calidad multiplataforma.

- Agrupar por **extensión** (incluidos `tar.gz` y `no-extension`) o **categoría** (Documents, Images, Videos, Archives, Audio, Other).
- Configurar categorías nuevas con parámetros CLI o **YAML** versionado.
- Agrupar opcionalmente por fecha de modificación en **UTC** (`AAAA/MM`).
- Seleccionar carpetas de origen y destino independientes.
- Buscar en subdirectorios con `--recursive` sin seguir enlaces simbólicos.
- Excluir archivos o directorios mediante patrones glob sin distinguir mayúsculas.
- Previsualizar con `--dry-run` sin crear archivos, carpetas o manifiestos.
- Resolver nombres duplicados con sufijos y evitar sobrescrituras de destinos preexistentes.
- Guardar un **manifiesto JSON persistente** con estados y SHA-256.
- Ejecutar `undo` con comprobación de integridad y conflictos, también con dry-run.
- Mostrar tablas Rich, totales de archivos movidos/omitidos y errores.

## Tecnologías e instalación

Python **3.14+**, Typer, Rich, PyYAML, pathlib y biblioteca estándar. pytest, Ruff, Hatchling y GitHub Actions aportan pruebas, calidad y distribución. No se necesita base de datos, cuenta externa ni credenciales.

~~~bash
git clone https://github.com/RamonRDR/fileflow-cli.git
cd fileflow-cli
python -m venv .venv
~~~

Active el entorno: PowerShell `.venv\Scripts\Activate.ps1`; Linux/macOS `source .venv/bin/activate`. Después:

~~~bash
python -m pip install -e .
fileflow --help
fileflow organize --help
fileflow undo --help
~~~

La implementación completa ya está disponible en la rama predeterminada, **`main`**. No existe una distribución publicada en PyPI. También puede usar `python -m fileflow`.

## Ejemplos de comandos

Simular sin modificar datos:

~~~bash
fileflow organize ./entrada --destination ./organizados --dry-run
~~~

Agrupar por extensión, categoría o fecha:

~~~bash
fileflow organize ./entrada -d ./organizados
fileflow organize ./entrada -d ./organizados --mode category
fileflow organize ./entrada -d ./organizados --by-date
~~~

Categorías nuevas, recursión y exclusiones:

~~~bash
fileflow organize ./entrada -d ./organizados --mode category --category "Investigacion=.pdf,.ipynb"
fileflow organize ./entrada -d ./organizados --recursive --exclude "*.tmp" --exclude "cache/**"
~~~

Configuración YAML:

~~~bash
fileflow organize ./entrada -d ./organizados --config examples/config.yaml --dry-run
fileflow organize ./entrada -d ./organizados --config examples/config.yaml
~~~

Cada ejecución real con archivos genera un manifiesto cuyo camino se imprime, como `<destino>/.fileflow/manifests/<id>.json`. Use la **ruta real** para comprobar y revertir:

~~~bash
fileflow undo "/ruta/organizados/.fileflow/manifests/<id>.json" --dry-run
fileflow undo "/ruta/organizados/.fileflow/manifests/<id>.json"
~~~

Son ejemplos, no resultados de ejecución inventados.

## Configuración YAML

~~~yaml
version: 1
mode: category
recursive: true
by_date: false
categories:
  Investigacion:
    - .pdf
    - .ipynb
exclude:
  - "*.tmp"
  - "cache/**"
~~~

Se rechazan claves desconocidas, valores del tipo incorrecto, extensiones y patrones inválidos. YAML se interpreta mediante `safe_load`. Las categorías personalizadas tienen prioridad sobre las predeterminadas y no se permite asignar explícitamente una extensión más de una vez. `--mode` de CLI prevalece sobre YAML; `--recursive`, `--by-date`, `--category` y `--exclude` activan o agregan reglas y no desactivan valores `true` existentes. Los patrones se comparan con nombres o rutas relativas utilizando barras `/`.

## Seguridad y undo

1. **Planificación sin cambios:** la simulación no escribe archivos ni crea un manifiesto.
2. **Rutas separadas:** se rechazan directorios iguales o superpuestos y enlaces elegidos directamente como raíz; los alias de directorios ancestrales (como /var en macOS) se normalizan, y se omiten enlaces encontrados durante el análisis y elementos ocultos.
3. **Sin reemplazos silenciosos:** se añaden sufijos a los conflictos planificados y se crean destinos exclusivamente (`xb`).
4. **Copiar antes de borrar el nombre original:** la copia se sincroniza, se comparan los SHA-256 de origen y destino y se revisan metadatos antes de retirar el origen.
5. **Registro previo:** el manifiesto existe antes de la primera copia y se actualiza tras cada resultado. Los lotes que podrían superar el límite de 10 MB se rechazan antes de mover archivos; divídalos en lotes menores.
6. **Reversión protegida:** se comprueba el tamaño y hash del destino y se rechaza cualquier ruta de origen que ya exista. Si se eliminó la carpeta original después de organizar, puede recrearse de forma segura al deshacer.

No hay comando para eliminación permanente. Aun así, un movimiento retira el nombre original después de copiar, y una reversión retira el nombre de destino después de restaurar. Haga copias de seguridad de archivos importantes.

**Limitaciones:** copiar y eliminar no es una transacción atómica. Un corte abrupto puede dejar archivos parciales o entradas `planned` que exigen conciliación manual; estas entradas nunca se deshacen automáticamente. No se garantiza protección frente a modificaciones simultáneas maliciosas. Consulte [Seguridad y limitaciones](docs/SECURITY.md).

Códigos de salida: `0` éxito/simulación; `1` fallos o conflictos; `2` configuración, rutas o manifiesto inválidos.

## Arquitectura

~~~text
src/fileflow/
  cli.py       Comandos Typer y salida Rich
  config.py    Configuración YAML
  rules.py     Categorías y exclusiones
  planner.py   Descubrimiento, rutas y planificación
  models.py    Modelos inmutables
  executor.py  Copia verificada
  journal.py   Manifiestos y reversión
tests/         pytest con tmp_path
examples/      YAML y demostración real
docs/          Seguridad y decisiones
.github/workflows/ci.yml   CI multiplataforma
~~~

Separar interfaz, reglas, planificación, ejecución y reversión permite pruebas aisladas. Lea las [decisiones técnicas](docs/DECISIONS.md).

## Pruebas y demostración real

~~~bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
python -m pytest -q
python -m build
python examples/wheel_smoke.py
python examples/demo.py
~~~

Las pruebas que modifican archivos usan `tmp_path` de pytest. La demostración crea directorios temporales y ejecuta los comandos reales de dry-run, organización con colisión, exclusiones y undo. Su salida auténtica aparece en **Demo CLI end-to-end** de [GitHub Actions](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml), en Ubuntu, Windows y macOS. No se inventan capturas ni métricas. El badge muestra el estado real de GitHub Actions en la rama principal; no implica publicación en PyPI ni despliegue en producción.

## Limitaciones conocidas

La copia y eliminación no son transaccionales ni completamente resistentes a cortes de energía. Los manifiestos incluyen rutas absolutas, son datos locales de confianza y no deben editarse. La recursión agrupa archivos por categoría/extensión sin conservar carpetas originales. Se ignoran elementos ocultos, enlaces y archivos especiales; las carpetas vacías permanecen. Se utiliza UTC. El manejo de permisos y nombres depende del sistema de archivos. La herramienta no sustituye un sistema de copias de seguridad.

## Licencia

[MIT](LICENSE). Copyright © 2026 Ramon Rodriguez.
