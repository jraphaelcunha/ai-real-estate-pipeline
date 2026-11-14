# AI Real Estate Pipeline — Subscrição Automatizada, Reconciliação e Despacho GIS

[![CI Quality Gate](https://github.com/jraphaelcunha/ai-real-estate-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/jraphaelcunha/ai-real-estate-pipeline)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![Contratos](https://img.shields.io/badge/Contracts-Pydantic%20v2-red)
![Licença: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Orquestração](https://img.shields.io/badge/Orchestration-LangChain-orange.svg)
![LLM](https://img.shields.io/badge/LLM-OpenAI%20GPT--4o--mini-green.svg)
![Integração](https://img.shields.io/badge/Integration-Monday.com%20GIS%20GraphQL-purple.svg)

> **[ Read in English ](README.md)**

## Sumário Executivo
O **AI Real Estate Pipeline** é um motor modular de triagem imobiliária, reconciliação financeira multi-documento e roteamento geoespacial para equipes de aquisições e corretagem. O sistema coleta listagens e pacotes de negócios, impõe contratos rígidos em **Pydantic v2**, cruza métricas financeiras entre **Offering Memorandum, Rent Roll e Resumo do Corretor** (com rastreabilidade de página), calcula reservas determinísticas de reforma e ARV, geocodifica endereços via **Geopy Nominatim** e despacha oportunidades qualificadas para o corretor mais próximo no **Monday.com** via GraphQL.

Para detalhes sobre decisões arquiteturais e trade-offs de design, consulte [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

> **Governança de Propriedade Intelectual (NDA):** Este repositório público é uma arquitetura de referência sanitizada e anonimizada. Regras proprietárias de clientes, credenciais de produção e documentos reais permanecem estritamente privados sob NDA; todos os dados em `data/raw_mock_data.json` e `eval/dataset/underwriting_v1.jsonl` são fixtures sintéticas para validação técnica e CI.

## Como Executar

```bash
pip install -r requirements.txt
python -m src.main
```

## Testes, Segurança e Avaliação

```bash
ruff check src/ tests/ eval/
bandit -r src/
pytest tests/ -v --cov=src --cov-report=term-missing
python eval/evaluate.py --dataset eval/dataset/underwriting_v1.jsonl --mock
```
