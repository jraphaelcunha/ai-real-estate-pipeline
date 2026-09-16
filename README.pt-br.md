# AI Real Estate Pipeline (Arquitetura Enterprise)

> **[ 🇺🇸 Read in English ](README.md)**

## Sumário Executivo
O **AI Real Estate Pipeline** é um agente autônomo de nível corporativo projetado para **imobiliárias, corretores e fundos de investimento imobiliário**. O sistema automatiza a varredura e extração de anúncios de imóveis dispersos na internet, normaliza dados não estruturados e gera uma **lista comparativa equiparada (preço por m², custos estimados de reforma e retorno pós-reforma - ARV)**. Além disso, utiliza inteligência geoespacial (Nominatim GIS) para mapear cada imóvel em quadros interativos no **Monday.com Enterprise** e despachar o negócio automaticamente para o corretor de campo mais próximo na região.

---

## 🎯 Proposta de Valor: Comparativo de Mercado & Despacho Geográfico

* **A Dor Real do Mercado:** Corretores e investidores perdem mais de 15 horas semanais navegando por portais imobiliários despadronizados. Comparar imóveis com descrições caóticas, avaliar o custo real de reformas e saber qual corretor deve visitar cada região é um gargalo lento e suscetível a erros.
* **Lista Comparativa Equiparada:** O pipeline extrai as variáveis críticas do imóvel e aplica contratos rígidos de dados (**Pydantic v2**) para calcular métricas financeiras essenciais: preço por metro quadrado, estimativa paramétrica de reforma e **ARV (After Repair Value)**, gerando um veredito objetivo (`COMPRAR`, `PASSAR` ou `INVESTIGAR`).
* **Mapeamento GIS & Roteamento para Corretores:** Os endereços são geocodificados com precisão em coordenadas de latitude e longitude via Geopy Nominatim, alimentando a visualização em mapa interativo do Monday.com e roteando o lead diretamente para o corretor mais próximo do imóvel.
* **Impacto Comercial:** Redução de 80% no tempo de triagem de oportunidades e resposta ágil para propostas de compra antes da concorrência.

---

## Principais Recursos Técnicos

### 1. Geocodificação Automatizada & Inteligência de Localização
*   **Mapeamento de Precisão**: Utiliza `geopy` (Nominatim) para converter automaticamente endereços em coordenadas precisas de Latitude/Longitude.
*   **Despacho Geoespacial**: Plota os imóveis na camada de mapa interativo do Monday.com e permite o roteamento automático de oportunidades baseado na proximidade do corretor.

### 2. Modelagem Financeira & Subscrição Cognitiva
*   **Lógica de Investimento com IA**: Utiliza modelos de linguagem via LangChain para extrair detalhes de vistorias e calcular métricas de viabilidade financeira (ARV e reformas) com validação estrita via Pydantic v2.
*   **Modo de Degradação Graciosa (Mock Fallback)**: Se a API de IA sofrer limitação de taxa (Rate Limit) ou falhas de conexão, o sistema entra em modo de avaliação heurística determinística sem travar o pipeline em lote.

### 3. Visualização Enterprise & Work OS
*   **Integração com Monday.com**: Envia dados estruturados para um Quadro Enterprise no Monday.com via GraphQL.
*   **Visualização em Mapa**: Preenche as **Visualizações de Mapa** interativas do Monday.com, permitindo que a liderança visualize clusters geográficos e o pipeline de negócios em tempo real.

## Tecnologias Utilizadas (Tech Stack)
*   **Core**: Python 3.12
*   **IA/LLM**: OpenAI GPT-4 (via LangChain)
*   **Geoespacial**: `geopy` (Nominatim)
*   **Integração**: Monday.com API v2 (GraphQL)
*   **Arquitetura**: Enterprise Board Architecture
*   **Validação**: Pydantic Strict Schemas

## Instalação

1.  **Clonar o Repositório**
    ```bash
    git clone https://github.com/jraphaelbarbosa/AI_Real_Estate_Pipeline.git
    cd AI_Real_Estate_Pipeline
    ```

2.  **Configurar o Ambiente Virtual**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **Instalar Dependências**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuração de Variáveis**
    Crie um arquivo `.env` na raiz do projeto:
    ```env
    OPENAI_API_KEY=sua_chave_openai
    MONDAY_API_KEY=sua_chave_monday
    ```

## Como Executar

Execute o pipeline completo de dados:

```bash
python -m src.main
```

**Fluxo de Trabalho:**
1.  **Ingestão**: Carrega dados brutos das propriedades.
2.  **Enriquecimento**: Geocodifica endereços para (Lat, Lon).
3.  **Análise**: A IA avalia a condição do imóvel e os dados financeiros.
4.  **Implantação**: Sincroniza os resultados no Dashboard e Mapa interativo do Monday.com.
