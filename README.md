# consulta-veicular

Script Python para consulta de histórico veicular completo usando **apenas a placa** como input (sem RENAVAM, sem CPF).

Usa a API paga [consultarplaca.com.br](https://consultarplaca.com.br/) para gerar um relatório detalhado equivalente aos serviços CheckAuto/DEKRA (~R$60), por cerca de **R$0.81 por consulta padrão**.

O módulo `sinesp.py` oferece uma camada gratuita via Sinesp Cidadão (dados básicos + roubo/furto), mas não está integrado ao `lookup.py` — veja a seção [Sinesp Cidadão](#sinesp-cidadão--camada-gratuita) abaixo.

---

## Dados cobertos

| Dado | Fonte | Flag | Custo |
|------|-------|------|-------|
| Dados cadastrais (marca, modelo, ano, cor, chassi, motor) | consultarplaca.com.br | padrão | ~R$0.31 |
| Roubo/furto, gravame, sinistro com perda total | consultarplaca.com.br | padrão | ~R$0.50 |
| Histórico de leilão detalhado (classificação A-D, IA danos, remarketing) | consultarplaca.com.br | `--leilao` | ~R$16.90 |
| Proprietário atual | consultarplaca.com.br | `--proprietario` | ~R$6.90 |
| Infrações RENAINF com valores | consultarplaca.com.br | `--renainf` | incluso |
| Situação roubo/furto + dados básicos | Sinesp Cidadão | standalone | **Grátis** |

**Custo típico por consulta:**
- Consulta padrão (sem leilão): **~R$0.81**
- Com leilão: **~R$17.71**
- Comparação: CheckAuto/DEKRA cobram ~R$60 pelo relatório equivalente

---

## Instalação

```bash
git clone https://github.com/seuusuario/consulta-veicular.git
cd consulta-veicular

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edite .env com suas credenciais
```

**Obter credenciais consultarplaca.com.br:**
1. Crie conta em [consultarplaca.com.br](https://consultarplaca.com.br/)
2. Vá em Minha Conta → API → Gerar API KEY
3. Configure `.env`:
   ```
   CONSULTARPLACA_EMAIL=seu@email.com
   CONSULTARPLACA_API_KEY=sua_chave
   ```

---

## Uso — lookup.py

```bash
# Placa de teste (não consome créditos)
python lookup.py AAA0000

# Consulta padrão: básico + roubo/furto + gravame + sinistro
python lookup.py BBJ1A73

# + histórico de leilão detalhado (classificação A-D, IA danos, remarketing)
python lookup.py BBJ1A73 --leilao

# + proprietário atual
python lookup.py BBJ1A73 --proprietario

# + infrações RENAINF com valores
python lookup.py BBJ1A73 --renainf

# Tudo de uma vez
python lookup.py BBJ1A73 --full

# Exportar resultado
python lookup.py BBJ1A73 --json           # salva BBJ1A73_<ts>.json
python lookup.py BBJ1A73 --full --md      # salva BBJ1A73_<ts>.md  (Markdown)
python lookup.py BBJ1A73 --full --pdf     # salva BBJ1A73_<ts>.pdf (requer fpdf2)
python lookup.py BBJ1A73 --full --json --md --pdf  # todos os três
```

---

## Sinesp Cidadão — camada gratuita

`sinesp.py` é um módulo **independente** que consulta o Sinesp Cidadão gratuitamente. Retorna situação de roubo/furto e dados básicos do veículo sem custo e sem RENAVAM.

### Limitações importantes

| Limitação | Detalhe |
|-----------|---------|
| **Requer IP brasileiro** | O servidor do governo bloqueia conexões de fora do Brasil. Use VPN com saída no Brasil se necessário. |
| **Endpoint não-oficial** | Usa o endpoint interno do app móvel SinespCidadao 3.0.2.1 (engenharia reversa). Pode quebrar a qualquer atualização do app. |
| **Não integrado ao lookup.py** | É um módulo standalone — `lookup.py` não o chama. Use diretamente (ver abaixo). |
| **Dados básicos apenas** | Não retorna histórico de leilão, gravame, RENAINF, proprietário ou débitos. |

### Uso como script

```bash
# Consulta simples (pretty-print)
python sinesp.py BBJ1A73

# Saída em JSON (útil para integração)
python sinesp.py BBJ1A73 --json

# Ajuda
python sinesp.py --help
```

**Saída esperada (quando acessível):**

```
Placa:          BBJ1A73
Situação:       Em circulação normal
Marca/Modelo:   VW/VOLKSWAGEN / UP TAKE MCV
Cor:            Branca
Ano fab/modelo: 2017 / 2018
Chassi:         9BWAG41****501585
Município:      CAMBE — PR
```

**Saída em JSON (`--json`):**

```json
{
  "fonte": "sinesp",
  "placa": "BBJ1A73",
  "situacao": "Em circulação normal",
  "restricoes": "",
  "marca": "VW/VOLKSWAGEN",
  "modelo": "UP TAKE MCV",
  "cor": "Branca",
  "ano_fabricacao": "2017",
  "ano_modelo": "2018",
  "municipio": "CAMBE",
  "uf": "PR",
  "chassi": "9BWAG41****501585"
}
```

**Em caso de erro (IP fora do Brasil):**

```json
{
  "erro": "Sinesp: falha de conexão. Verifique sua internet."
}
```

### Uso como módulo Python

```python
from sinesp import consultar

resultado = consultar("BBJ1A73")

if "erro" in resultado:
    print(f"Falhou: {resultado['erro']}")
else:
    print(resultado["situacao"])   # "Em circulação normal"
    print(resultado["marca"])      # "VW/VOLKSWAGEN"
    print(resultado["chassi"])     # parcialmente mascarado pela API
```

### Campos retornados

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `fonte` | str | Sempre `"sinesp"` |
| `placa` | str | Placa consultada |
| `situacao` | str | Ex: `"Em circulação normal"`, `"Roubo/Furto"` |
| `restricoes` | str | Restrições (texto livre) ou `""` |
| `marca` | str | Fabricante |
| `modelo` | str | Modelo |
| `cor` | str | Cor predominante |
| `ano_fabricacao` | str | Ano de fabricação |
| `ano_modelo` | str | Ano do modelo |
| `municipio` | str | Município de emplacamento |
| `uf` | str | UF do município |
| `chassi` | str | Chassi (parcialmente mascarado) |

---

## Exemplo de saída terminal (lookup.py)

```
══════════════ RELATÓRIO VEICULAR — BBJ1A73 — 2026-02-26 18:05 ══════════════

┌─ DADOS DO VEÍCULO ──────────────────────────────────────────────────────────┐
│ Marca / Modelo    VW / UP TAKE MCV                                          │
│ Ano Fab / Modelo  2017 / 2018                                               │
│ Cor               Branca                                                    │
│ Combustível       FLEX                                                      │
│ Chassi            9BWAG4128JT501585                                         │
│ Motor             CSE220128                                                 │
│ Município         CAMBE — PR                                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ ROUBO / FURTO ─────────────────────────────────────────────────────────────┐
│ Status            NADA CONSTA ✅                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ GRAVAME / ALIENAÇÃO FIDUCIÁRIA ────────────────────────────────────────────┐
│ Gravame / Alienação    NADA CONSTA ✅                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Alerta de leilão com seguradora:**
```
┌─ LEILÃO ⚠️  REGISTRO ENCONTRADO ───────────────────────────────────────────┐
│ Registro de Leilão    CONSTA ⚠️                                             │
│ Classificação         C — Batida grave / possível perda total               │
│ Comitente             PORTO SEGURO CIA DE SEGUROS GERAIS ← seguradora       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Estrutura do projeto

```
consulta-veicular/
├── lookup.py        # CLI — entry point principal
├── client.py        # Wrapper consultarplaca.com.br (autenticação, endpoints, parsers)
├── sinesp.py        # Sinesp Cidadão — módulo standalone gratuito (não integrado ao lookup.py)
├── report.py        # Saída: terminal Rich + JSON + Markdown + PDF
├── requirements.txt # requests, python-dotenv, rich, fpdf2
├── .env.example     # Template de configuração
└── .gitignore
```

---

## Arquitetura

```
lookup.py (CLI)
  │
  ├── client.py ──▶ consultarplaca.com.br API
  │   ├── dados_basicos()       GET /consultarPlaca
  │   ├── roubo_furto()         GET /consultarHistoricoRouboFurto
  │   ├── gravame()             GET /consultarGravame
  │   ├── sinistro()            GET /consultarSinistroComPerdaTotal
  │   ├── leilao()              GET /consultarRegistroLeilaoPrime   (--leilao)
  │   ├── proprietario()        GET /consultarProprietarioAtual     (--proprietario)
  │   └── renainf()             GET /consultarRegistrosInfracoesRenainf (--renainf)
  │
  └── report.py
      ├── imprimir_relatorio()  terminal (Rich)
      ├── salvar_json()         --json
      ├── salvar_markdown()     --md
      └── salvar_pdf()          --pdf  (fpdf2)

sinesp.py (standalone — não chamado pelo lookup.py)
  └── consultar()  ──▶ cidadao.sinesp.gov.br (grátis, requer IP brasileiro)
```

---

## Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `CONSULTARPLACA_EMAIL` | Sim | Email da conta em consultarplaca.com.br |
| `CONSULTARPLACA_API_KEY` | Sim | Token gerado em Minha Conta → API |

Armazene em `.env` (nunca commite este arquivo):
```
CONSULTARPLACA_EMAIL=seu@email.com
CONSULTARPLACA_API_KEY=sua_chave_aqui
```

---

## Notas

- **RENAVAM não é necessário** — as APIs fazem o lookup internamente pela placa
- **Sinesp Cidadão requer IP brasileiro** — use VPN com saída no Brasil se necessário
- **Placa de teste**: `AAA0000` (sem consumo de créditos, chassi `00AAA00A00A000000`)
- FIPE não está incluso — disponível gratuitamente em qualquer site de tabela FIPE
- O portal SENATRAN exige CPF/CNPJ do proprietário — inacessível para consulta de terceiros
