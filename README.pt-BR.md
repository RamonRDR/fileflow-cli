# FileFlow CLI

[![CI](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/RamonRDR/fileflow-cli/actions/workflows/ci.yml)

**Organizador de arquivos via terminal, com foco em segurança e compatibilidade com Windows, Linux e macOS.**

Idiomas: [English](README.md) | **Português (Brasil)** | [Español](README.es.md)

> **Estado: MVP do Ciclo 1 em revisão.** Configuração YAML, execução recursiva, exclusões, manifesto e desfazer (`undo`) pertencem ao Ciclo 2 e ainda não estão disponíveis. O pacote não está publicado no PyPI.

## Funcionalidades

Organização por extensão ou categorias padrão (Documents, Images, Videos, Archives, Audio e Other); categorias personalizadas com `--category`; agrupamento opcional por mês e ano da modificação em UTC; escolha independente da origem e do destino; prévia com `--dry-run`; nomes duplicados com sufixos numerados; bloqueio de sobrescrita. Arquivos ocultos, subpastas e links simbólicos são ignorados no MVP.

## Tecnologias

Python 3.14+, Typer, Rich, pathlib e biblioteca padrão. pytest para testes, Ruff para qualidade, Hatchling para empacotamento e GitHub Actions para CI. PyYAML só será adicionado quando a configuração YAML for implementada.

## Instalação

~~~bash
git clone https://github.com/RamonRDR/fileflow-cli.git
cd fileflow-cli
python -m venv .venv
# Ative o ambiente virtual conforme seu sistema operacional.
python -m pip install -e .
fileflow --help
~~~

Enquanto o PR inicial não for integrado, utilize a branch `feat/cycle-1-safe-file-organizer` para testar a implementação.

## Exemplos

Simular, sem alterar arquivos:

~~~bash
fileflow organize ./entrada --destination ./organizados --dry-run
~~~

Executar por extensão ou categoria:

~~~bash
fileflow organize ./entrada -d ./organizados
fileflow organize ./entrada -d ./organizados --mode category
fileflow organize ./entrada -d ./organizados --mode category --category "Pesquisa=.pdf,.ipynb"
fileflow organize ./entrada -d ./organizados --by-date
~~~

A CLI exibe as operações em uma tabela Rich e resume arquivos movidos, ignorados e falhas. Códigos de saída: `0` sucesso/simulação, `1` falhas parciais, `2` entrada inválida.

## YAML e undo

**Ainda não implementados.** No Ciclo 2, o YAML permitirá configurar categorias e exclusões; um manifesto persistente permitirá desfazer operações verificando conflitos. Não execute este MVP esperando um comando de recuperação automática.

## Segurança

O planejamento não grava dados. Origem e destino iguais ou sobrepostos são recusados; caminhos contendo links simbólicos são bloqueados. O destino é aberto em modo exclusivo, sem substituir arquivos existentes. Os dados são copiados e conferidos por metadados antes de excluir o arquivo original. Se uma operação falha, a origem é preservada normalmente. Faça backup dos arquivos importantes e execute `--dry-run` primeiro.

## Arquitetura

`cli.py`: interface; `models.py`: modelos imutáveis; `rules.py`: regras; `planner.py`: planejamento e validação; `executor.py`: movimentação segura; `tests/`: testes temporários e isolados.

## Testes

~~~bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
python -m pytest -q
python -m build
~~~

O CI usa Python 3.14 em Ubuntu, Windows e macOS. Todos os testes que manipulam arquivos utilizam `tmp_path` do pytest, sem diretórios pessoais.

## Limitações conhecidas

Não há recursão, exclusões, YAML, histórico ou undo neste ciclo. A ferramenta ignora arquivos ocultos e links. Movimentos por cópia e remoção não são transacionais: interrupções abruptas podem deixar arquivos parciais no destino. As verificações de permissões e alterações concorrentes são de melhor esforço; ataques com modificações maliciosas simultâneas do sistema de arquivos não estão cobertos.

## Licença

MIT. Consulte [LICENSE](LICENSE).
