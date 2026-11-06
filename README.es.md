# FileFlow CLI

[![CI](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)

**Organizador de archivos de línea de comandos, diseñado para Windows, Linux y macOS con medidas de seguridad.**

Idiomas: [English](README.md) | [Português (Brasil)](README.pt-BR.md) | **Español**

> **Estado: MVP del Ciclo 1 en revisión.** YAML, organización recursiva, exclusiones, manifiestos y `undo` pertenecen al Ciclo 2 y todavía no están disponibles. El proyecto no está publicado en PyPI.

## Funcionalidades

Organización por extensión o categorías (Documents, Images, Videos, Archives, Audio y Other); categorías personalizadas mediante `--category`; agrupación opcional por año y mes de modificación en UTC; directorios de origen y destino independientes; simulación `--dry-run`; resolución de duplicados con sufijos numerados y protección contra sobrescritura. El MVP omite archivos ocultos, subdirectorios y enlaces simbólicos.

## Tecnologías

Python 3.14+, Typer, Rich, pathlib y biblioteca estándar. pytest para pruebas, Ruff para calidad, Hatchling para distribución y GitHub Actions para CI. PyYAML se incorporará cuando se implemente YAML.

## Instalación

~~~bash
git clone https://github.com/RamonRDR/fileflow-cli.git
cd fileflow-cli
python -m venv .venv
# Active el entorno virtual según su sistema operativo.
python -m pip install -e .
fileflow --help
~~~

Hasta que se integre el primer PR, utilice la rama `feat/cycle-1-safe-file-organizer` para evaluar el MVP.

## Ejemplos

Vista previa sin modificar archivos:

~~~bash
fileflow organize ./entrada --destination ./organizados --dry-run
~~~

Organizar por extensión, categoría o fecha:

~~~bash
fileflow organize ./entrada -d ./organizados
fileflow organize ./entrada -d ./organizados --mode category
fileflow organize ./entrada -d ./organizados --mode category --category "Investigacion=.pdf,.ipynb"
fileflow organize ./entrada -d ./organizados --by-date
~~~

La interfaz muestra una tabla Rich y un resumen de archivos movidos, omitidos y fallidos. Códigos: `0` éxito o simulación, `1` fallos de movimiento, `2` argumentos o rutas inválidos.

## Configuración YAML y undo

**Planificados para el Ciclo 2, no implementados.** YAML permitirá definir categorías y exclusiones; el comando `undo` utilizará un manifiesto persistente y verificará conflictos. Esta versión no puede revertir automáticamente movimientos anteriores.

## Seguridad

El plan no modifica archivos. Se prohíben rutas de origen y destino iguales o superpuestas, y rutas con enlaces simbólicos. La creación exclusiva del destino impide reemplazar archivos existentes. Se copia el contenido y se verifican metadatos antes de retirar el original. Normalmente, un fallo conserva el archivo de origen. Realice copias de seguridad y pruebe siempre `--dry-run` antes de ejecutar.

## Arquitectura

`cli.py`: comandos; `models.py`: estructuras inmutables; `rules.py`: categorías; `planner.py`: validación y planificación; `executor.py`: operaciones; `tests/`: pruebas aisladas con archivos temporales.

## Pruebas y calidad

~~~bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
python -m pytest -q
python -m build
~~~

CI ejecuta Python 3.14 en Ubuntu, Windows y macOS; las pruebas de archivos usan únicamente `tmp_path`.

## Limitaciones conocidas

Sin recursión, exclusiones, configuración YAML, registro persistente ni undo en este ciclo. Se omiten archivos ocultos y enlaces. Copiar y borrar no constituye una transacción atómica; una interrupción brusca puede dejar un archivo de destino incompleto. La comprobación de permisos y de cambios simultáneos es limitada; los ataques maliciosos de modificación concurrente del sistema de archivos quedan fuera del modelo de amenazas actual.

## Licencia

MIT. Consulte [LICENSE](LICENSE).
