<div align="center">

# FileFlow CLI 📁

**Organize arquivos com segurança. Simule cada movimentação. Desfaça com confiança.**

[🇺🇸 English](README.md) · [🇧🇷 Português](README.pt-BR.md) · [🇪🇸 Español](README.es.md)

[![CI](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)
[![Python 3.14](https://img.shields.io/badge/Python-3.14-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-0.1.0-555555)](pyproject.toml)
[![MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[![Typer](https://img.shields.io/badge/Typer-CLI-7c3aed)](https://typer.tiangolo.com/)
[![Rich](https://img.shields.io/badge/Rich-terminal-f59e0b)](https://github.com/Textualize/rich)
[![PyYAML](https://img.shields.io/badge/PyYAML-config-ef4444)](https://pyyaml.org/)
[![Hatchling](https://img.shields.io/badge/Hatchling-build%20backend-4b5563)](pyproject.toml)

[![pytest](https://img.shields.io/badge/pytest-92%20passing-0ea5e9)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/badge/Ruff-lint%20%2B%20format-111827)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)
[![Build](https://img.shields.io/badge/build-wheel%20verified-2563eb)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)
[![CLI smoke](https://img.shields.io/badge/CLI-smoke%20tested-14b8a6)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)
[![E2E demo](https://img.shields.io/badge/E2E%20demo-verified-0f766e)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)
[![Platforms](https://img.shields.io/badge/platforms-Windows%20%7C%20Linux%20%7C%20macOS-blue)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)

</div>

> **Estado:** desenvolvimento concluído, revisão final do Codex realizada e código integrado à `main`. GitHub Actions aprovado em Windows, Ubuntu e macOS (92 testes por plataforma). O pacote ainda não foi publicado no PyPI.

## Funcionalidades

O FileFlow é uma automação multiplataforma em Python, criada para uso real e demonstração de boas práticas de desenvolvimento.

- Organizar por **extensão** (incluindo `tar.gz` e `no-extension`) ou **categoria** (Documents, Images, Videos, Archives, Audio e Other).
- Personalizar categorias com flags repetíveis ou arquivo **YAML** versionado.
- Organizar opcionalmente por ano/mês de modificação em **UTC**.
- Escolher diretórios independentes de origem e destino.
- Percorrer subpastas com `--recursive` sem seguir links simbólicos.
- Excluir arquivos e pastas com padrões glob, sem distinção entre maiúsculas e minúsculas.
- Visualizar o plano com `--dry-run` sem criar arquivos, diretórios ou manifestos.
- Resolver nomes duplicados com sufixos e impedir sobrescrita mesmo diante de conflitos surgidos depois do planejamento.
- Manter um **manifesto JSON persistente** por execução, incluindo status e SHA-256.
- Executar `undo` verificando colisões, tamanho e conteúdo, também com dry-run.
- Mostrar tabelas Rich, resumo de movimentações, arquivos ignorados e falhas.

## Stack tecnológica

Python **3.14+**, Typer, Rich, PyYAML, pathlib e biblioteca padrão. pytest, Ruff, Hatchling e GitHub Actions compõem a camada de qualidade. Não há banco de dados, chave de API ou serviço externo. A versão de código declarada no `pyproject.toml` é **0.1.0**, sem publicação no PyPI.

## Instalação

Clone a versão atual da `main`:

~~~bash
git clone https://github.com/RamonRDR/fileflow-cli.git
cd fileflow-cli
python -m venv .venv
~~~

Ative o ambiente: PowerShell `.venv\Scripts\Activate.ps1`; Linux/macOS `source .venv/bin/activate`. Depois:

~~~bash
python -m pip install -e .
fileflow --help
fileflow organize --help
fileflow undo --help
~~~

A implementação completa está disponível na branch padrão, **`main`**. O pacote **não** está publicado no PyPI. O comando `python -m fileflow` também funciona.

## Primeiros passos

Simular sem alterar nada:

~~~bash
fileflow organize ./entrada --destination ./organizados --dry-run
~~~

Organizar por extensão, categoria ou data:

~~~bash
fileflow organize ./entrada -d ./organizados
fileflow organize ./entrada -d ./organizados --mode category
fileflow organize ./entrada -d ./organizados --by-date
~~~

Adicionar categoria, recursão e exclusões:

~~~bash
fileflow organize ./entrada -d ./organizados --mode category --category "Pesquisa=.pdf,.ipynb"
fileflow organize ./entrada -d ./organizados --recursive --exclude "*.tmp" --exclude "cache/**"
~~~

Usar regras YAML:

~~~bash
fileflow organize ./entrada -d ./organizados --config examples/config.yaml --dry-run
fileflow organize ./entrada -d ./organizados --config examples/config.yaml
~~~

A execução real com arquivos produz um manifesto cujo caminho é impresso no terminal, como `<destino>/.fileflow/manifests/<id>.json`. Use o **caminho verdadeiro informado pelo programa**:

~~~bash
fileflow undo "/caminho/organizados/.fileflow/manifests/<id>.json" --dry-run
fileflow undo "/caminho/organizados/.fileflow/manifests/<id>.json"
~~~

Os caminhos acima são exemplos, não saídas inventadas.

## Configuração YAML

~~~yaml
version: 1
mode: category
recursive: true
by_date: false
categories:
  Pesquisa:
    - .pdf
    - .ipynb
exclude:
  - "*.tmp"
  - "cache/**"
~~~

O esquema rejeita chaves desconhecidas, tipos incorretos, extensões e padrões inválidos. O PyYAML usa `safe_load`. Categorias padrão permanecem disponíveis, mas extensões atribuídas explicitamente ganham prioridade; duplicações explícitas são recusadas. `--mode` prevalece sobre o modo do YAML; `--recursive`, `--by-date`, `--category` e `--exclude` habilitam ou acrescentam regras, sem desativar valores `true` no arquivo. Os padrões consideram nomes e caminhos relativos, com `/` como separador.

## Segurança e undo

1. **Planejamento sem escrita:** o dry-run não grava arquivos nem cria manifestos.
2. **Diretórios separados:** origem e destino iguais ou aninhados são recusados; links usados diretamente como raiz são bloqueados, aliases de ancestrais (como /var no macOS) são normalizados, e links encontrados na varredura e itens ocultos são ignorados.
3. **Sem sobrescrita silenciosa:** colisões planejadas recebem sufixos, e a gravação exclusiva `xb` impede substituir arquivos existentes.
4. **Copiar antes de remover:** a cópia é sincronizada e seu SHA-256 é comparado com o da origem antes de remover o caminho original, com nova verificação de metadados.
5. **Registro antecipado:** o manifesto é criado antes da primeira movimentação e atualizado após cada operação. Lotes que poderiam ultrapassar o limite de 10 MB são recusados antes de movimentar arquivos; divida-os em lotes menores.
6. **Desfazer protegido:** somente movimentações registradas podem ser restauradas; se a origem já tiver arquivo ou o destino tiver mudado, a operação é recusada. Uma pasta de origem removida após a organização pode ser recriada durante a restauração.

Não existe comando para exclusão permanente. Mesmo assim, o nome original é removido após a cópia e o nome de destino é removido após a reversão. Faça backup de arquivos importantes antes de executar.

**Limite importante:** copiar e remover não é uma transação atômica. Interrupções podem deixar arquivos parciais e operações `planned` no manifesto, exigindo reconciliação manual. Elas não são desfeitas automaticamente. Não há defesa completa contra alterações maliciosas simultâneas dos diretórios. Leia [Segurança e limitações](docs/SECURITY.md).

Códigos de saída: `0` sucesso/simulação; `1` erro operacional ou conflito de undo; `2` entrada, configuração ou manifesto inválido.

## Arquitetura do projeto

~~~text
src/fileflow/
  cli.py       Interface Typer e Rich
  config.py    Validação YAML
  rules.py     Categorias e exclusões
  planner.py   Planejamento e validação de caminhos
  models.py    Modelos imutáveis
  executor.py  Cópia segura e verificação
  journal.py   Registro persistente e reversão
  __main__.py  Execução com python -m fileflow
tests/         pytest com tmp_path
examples/      YAML e demonstração executável
docs/          Segurança e decisões de engenharia
.github/workflows/ci.yml   CI multiplataforma
~~~

O projeto separa apresentação, regras, planejamento, execução e reversão. Consulte [Decisões técnicas](docs/DECISIONS.md).

## Testes, empacotamento e demonstração real

~~~bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
python -m pytest -q
python -m build
python examples/wheel_smoke.py
python examples/demo.py
~~~

Os testes usam apenas diretórios temporários do pytest. O demo executa a CLI real em `TemporaryDirectory`, demonstra dry-run, movimentação com nome duplicado, exclusões e undo. A saída verdadeira aparece na etapa **Demo CLI end-to-end** do [GitHub Actions](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml) em Windows, Linux e macOS. Não há capturas ou resultados inventados. O badge acompanha o estado do workflow da branch principal; não significa publicação no PyPI ou implantação em produção.

**Manutenção dos badges:** o badge do pytest registra **92 testes aprovados por plataforma**, conforme a [execução #42732136463 do GitHub Actions](https://github.com/RamonRDR/fileflow-cli/actions/runs/42732136463). O CI gera JUnit XML e verifica a quantidade nas três versões. Ao alterar os testes, atualize todos os badges no mesmo PR. Consulte o [inventário dos badges](docs/BADGES.md).

## Limitações conhecidas

- A cópia seguida de remoção não é uma transação atômica; falhas repentinas podem deixar cópias parciais ou registros desatualizados no manifesto.
- A ferramenta não oferece proteção completa contra trocas maliciosas de diretórios, organizadores concorrentes ou todos os comportamentos de sistemas de arquivos em rede.
- Confie apenas em manifestos locais criados por você: eles contêm caminhos absolutos e não devem ser editados nem compartilhados sem cuidado.
- A execução recursiva agrupa arquivos por categoria/extensão, **sem preservar a hierarquia** original; pastas vazias permanecem.
- Arquivos ocultos, links simbólicos e arquivos especiais são ignorados. Os agrupamentos por data usam UTC.
- Regras de nomes, colisões e permissões dependem do sistema de arquivos e da plataforma.
- Esta é uma ferramenta de automação local, não um sistema de backup corporativo.

## Licença

[MIT](LICENSE). Copyright © 2026 Ramon Rodriguez.
