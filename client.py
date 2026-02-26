"""
Wrapper para a API consultarplaca.com.br (v2)

Base URL: https://api.consultarplaca.com.br/v2
Auth:     Basic Auth — email como usuário, API key como senha
Docs:     https://docs.consultarplaca.com.br/
"""

import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.consultarplaca.com.br/v2"

PLACA_RE = re.compile(r"^[A-Z]{3}\d{4}$|^[A-Z]{3}\d[A-Z]\d{2}$")


class ConsultarPlacaError(Exception):
    """Erro da API consultarplaca.com.br.
    Atributo `tipo` contém o valor de tipo_do_erro quando disponível."""
    def __init__(self, message: str, tipo: str = ""):
        super().__init__(message)
        self.tipo = tipo


class ConsultarPlacaClient:
    """
    Cliente para a API consultarplaca.com.br v2.

    Credenciais lidas de:
      CONSULTARPLACA_EMAIL   — email da conta (usuário do Basic Auth)
      CONSULTARPLACA_API_KEY — chave gerada em Minha Conta → API

    Placa de teste (não consome créditos): AAA0000
    Chassi de teste:                        00AAA00A00A000000
    """

    def __init__(self, email: str | None = None, api_key: str | None = None):
        self.email = email or os.getenv("CONSULTARPLACA_EMAIL", "")
        self.api_key = api_key or os.getenv("CONSULTARPLACA_API_KEY", "")

        if not self.email:
            raise ConsultarPlacaError(
                "CONSULTARPLACA_EMAIL não definido. "
                "Configure em .env: CONSULTARPLACA_EMAIL=seu@email.com"
            )
        if not self.api_key:
            raise ConsultarPlacaError(
                "CONSULTARPLACA_API_KEY não definida. "
                "Configure em .env: CONSULTARPLACA_API_KEY=sua_chave"
            )

        self.session = requests.Session()
        self.session.auth = (self.email, self.api_key)
        self.session.headers.update({"Accept": "application/json"})

    # ─── Transporte ───────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict, timeout: int = 20) -> dict:
        url = f"{BASE_URL}/{path}"
        try:
            resp = self.session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            try:
                body = e.response.json()
                msg = body.get("mensagem", e.response.text[:300])
                tipo = body.get("tipo_do_erro", "")
            except Exception:
                msg, tipo = e.response.text[:300], ""
            raise ConsultarPlacaError(f"HTTP {e.response.status_code}: {msg}", tipo)
        except requests.exceptions.ConnectionError:
            raise ConsultarPlacaError("Falha de conexão com api.consultarplaca.com.br.")
        except requests.exceptions.Timeout:
            raise ConsultarPlacaError(f"Timeout ({timeout}s) — api.consultarplaca.com.br.")
        except ValueError as e:
            raise ConsultarPlacaError(f"Resposta não-JSON: {e}")

        # HTTP 200 mas com erro lógico — checar campo status
        if data.get("status") == "erro":
            tipo = data.get("tipo_do_erro", "")
            msg = data.get("mensagem", tipo or "Erro desconhecido")
            raise ConsultarPlacaError(f"{tipo}: {msg}" if tipo else msg, tipo)

        return data

    # ─── Endpoints ────────────────────────────────────────────────────────────

    def dados_basicos(self, placa: str) -> dict:
        """
        GET /consultarPlaca — dados cadastrais do veículo.
        Retorna marca/modelo/ano/cor/chassi/motor/segmento/procedência/município.
        """
        placa = _validar_placa(placa)
        raw = self._get("consultarPlaca", {"placa": placa})
        return _parse_dados_basicos(raw)

    def roubo_furto(self, placa: str) -> dict:
        """
        GET /consultarHistoricoRouboFurto — histórico de roubo/furto.
        Retorna registros com BO, data, tipo de ocorrência e UF.
        """
        placa = _validar_placa(placa)
        raw = self._get("consultarHistoricoRouboFurto", {"placa": placa})
        return _parse_roubo_furto(raw)

    def gravame(self, placa: str) -> dict:
        """
        GET /consultarGravame — gravame / alienação fiduciária.
        Retorna se há financiamento ativo, agente financeiro (banco), CNPJ, data.
        """
        placa = _validar_placa(placa)
        raw = self._get("consultarGravame", {"placa": placa})
        return _parse_gravame(raw)

    def sinistro(self, placa: str) -> dict:
        """
        GET /consultarSinistroComPerdaTotal — ocorrência de sinistro com perda total.
        Retorna sim/nao/indisponivel + descrição.
        """
        placa = _validar_placa(placa)
        raw = self._get("consultarSinistroComPerdaTotal", {"placa": placa})
        return _parse_sinistro(raw)

    def leilao(self, placa: str) -> dict:
        """
        GET /consultarRegistroLeilaoPrime — histórico de leilão detalhado.
        Retorna: registros de leilão (comitente, lote, data), classificação A-D,
        remarketing, análise de danos por IA e fotos.
        Aviso: timeout longo recomendado quando possui_registro=sim (processamento de imagens).
        """
        placa = _validar_placa(placa)
        # Timeout estendido: docs recomendam min 300s quando há imagens
        raw = self._get("consultarRegistroLeilaoPrime", {"placa": placa}, timeout=300)
        return _parse_leilao(raw)

    def proprietario(self, placa: str) -> dict:
        """
        GET /consultarProprietarioAtual — proprietário atual.
        Nome e documento (parcialmente mascarado). Não identifica pessoa física completa.
        """
        placa = _validar_placa(placa)
        raw = self._get("consultarProprietarioAtual", {"placa": placa})
        return _parse_proprietario(raw)

    def renainf(self, placa: str) -> dict:
        """
        GET /consultarRegistrosInfracoesRenainf — débitos por infrações RENAINF.
        Retorna lista de infrações com valor, órgão, local, datas.
        """
        placa = _validar_placa(placa)
        raw = self._get("consultarRegistrosInfracoesRenainf", {"placa": placa})
        return _parse_renainf(raw)

    def consultar_chassi(self, chassi: str) -> dict:
        """
        GET /consultarChassi — consulta por número de chassi (8-17 caracteres).
        Retorna os mesmos dados de dados_basicos().
        """
        chassi = chassi.strip().upper()
        if not re.match(r"^[A-Z0-9]{8,17}$", chassi):
            raise ValueError(f"Chassi inválido: '{chassi}'. Use 8 a 17 caracteres alfanuméricos.")
        raw = self._get("consultarChassi", {"chassi": chassi})
        return _parse_dados_basicos(raw)  # mesma estrutura que consultarPlaca


# ─── Validação ────────────────────────────────────────────────────────────────

def _validar_placa(placa: str) -> str:
    clean = re.sub(r"[^A-Z0-9]", "", placa.upper())
    if not PLACA_RE.match(clean):
        raise ValueError(f"Placa inválida: '{placa}'. Use ABC1234 (antiga) ou ABC1D23 (Mercosul).")
    return clean


# ─── Parsers — extraem dados do envelope {"status","dados",...} ───────────────

def _parse_dados_basicos(raw: dict) -> dict:
    info = raw.get("dados", {}).get("informacoes_veiculo", {})
    veiculo = info.get("dados_veiculo", {})
    tecnicos = info.get("dados_tecnicos", {})
    carga = info.get("dados_carga", {})
    return {
        "fonte": "consultarplaca/basico",
        "data_solicitacao": raw.get("data_solicitacao", ""),
        # Dados do veículo
        "placa": veiculo.get("placa", ""),
        "chassi": veiculo.get("chassi", ""),
        "ano_fabricacao": veiculo.get("ano_fabricacao", ""),
        "ano_modelo": veiculo.get("ano_modelo", ""),
        "marca": veiculo.get("marca", ""),
        "modelo": veiculo.get("modelo", ""),
        "cor": veiculo.get("cor", ""),
        "segmento": veiculo.get("segmento", ""),
        "combustivel": veiculo.get("combustivel", ""),
        "procedencia": veiculo.get("procedencia", ""),
        "municipio": veiculo.get("municipio", ""),
        "uf": veiculo.get("uf_municipio", ""),
        # Dados técnicos
        "tipo_veiculo": tecnicos.get("tipo_veiculo", ""),
        "sub_segmento": tecnicos.get("sub_segmento", ""),
        "numero_motor": tecnicos.get("numero_motor", ""),
        "numero_caixa_cambio": tecnicos.get("numero_caixa_cambio", ""),
        "potencia": tecnicos.get("potencia", ""),
        "cilindradas": tecnicos.get("cilindradas", ""),
        # Dados de carga
        "numero_eixos": carga.get("numero_eixos", ""),
        "capacidade_maxima_tracao": carga.get("capacidade_maxima_tracao", ""),
        "capacidade_passageiro": carga.get("capacidade_passageiro", ""),
        "_raw": raw,
    }


def _parse_roubo_furto(raw: dict) -> dict:
    hist = raw.get("dados", {}).get("historico_roubo_furto", {})
    reg = hist.get("registros_roubo_furto", {})
    possui = reg.get("possui_registro", "indisponivel")
    registros = reg.get("registros", []) or []
    return {
        "fonte": "consultarplaca/roubo_furto",
        "possui_registro": possui,        # "sim" | "nao" | "indisponivel"
        "registros": [
            {
                "boletim_ocorrencia": r.get("boletim_ocorrencia", ""),
                "data": r.get("data_boletim_ocorrencia", ""),
                "tipo": r.get("tipo_ocorrencia", ""),
                "uf": r.get("uf_ocorrencia", ""),
            }
            for r in registros
        ],
        "_raw": raw,
    }


def _parse_gravame(raw: dict) -> dict:
    g = raw.get("dados", {}).get("gravame", {})
    possui = g.get("possui_gravame", "indisponivel")
    reg = g.get("registro") or {}
    agente = reg.get("agente_financeiro", {}) if reg else {}
    return {
        "fonte": "consultarplaca/gravame",
        "possui_gravame": possui,          # "sim" | "nao" | "indisponivel"
        "agente_financeiro": agente.get("nome", ""),
        "cnpj_agente": agente.get("cnpj", ""),
        "data_registro": reg.get("data_registro", "") if reg else "",
        "uf_placa": reg.get("uf_placa", "") if reg else "",
        "situacao": reg.get("situacao", "") if reg else "",
        "_raw": raw,
    }


def _parse_sinistro(raw: dict) -> dict:
    s = raw.get("dados", {}).get("registro_sinistro_com_perda_total", {})
    return {
        "fonte": "consultarplaca/sinistro",
        "possui_registro": s.get("possui_registro", "indisponivel"),  # "sim"|"nao"|"indisponivel"
        "descricao": s.get("registro", ""),
        "_raw": raw,
    }


def _parse_leilao(raw: dict) -> dict:
    info = raw.get("dados", {}).get("informacoes_sobre_leilao", {})
    possui = info.get("possui_registro", "indisponivel")

    # Classificação geral A/B/C/D
    oferta = info.get("registro_sobre_oferta", {}) or {}
    classificacao = oferta.get("classificacao", "")
    dicionario = oferta.get("dicionario_classificacoes", {}) or {}

    # Registros individuais de leilão
    reg_leiloes = info.get("registro_leiloes", {}) or {}
    leiloes = reg_leiloes.get("registros", []) or []

    # Sinistros/acidentes (flag rápido dentro da resposta de leilão)
    sin_acid = info.get("registro_sinistros_acidentes", {}) or {}

    # Parecer técnico
    parecer_obj = info.get("parecer_tecnico", {}) or {}
    detalhes_parecer = parecer_obj.get("detalhes", {}) or {}

    # Remarketing
    remarketing = raw.get("dados", {}).get("informacoes_sobre_remarketing", {}) or {}
    rem_registros = remarketing.get("registros", []) or []

    # Danos detectados por IA
    ia = raw.get("dados", {}).get("informacoes_possiveis_danos_detectados_por_ia", {}) or {}

    return {
        "fonte": "consultarplaca/leilao",
        "possui_registro": possui,
        "classificacao": classificacao,       # "A"|"B"|"C"|"D"|"N"|""
        "dicionario_classificacoes": dicionario,
        "leiloes": [
            {
                "comitente": l.get("comitente", ""),
                "lote": l.get("lote", ""),
                "data_leilao": l.get("data_leilao", ""),
                "classificacao": l.get("classi", ""),
                "segmento": l.get("segmento", ""),
                "ano_fabricacao": l.get("ano_fabricacao", ""),
                "ano_modelo": l.get("ano_modelo", ""),
            }
            for l in leiloes
        ],
        "sinistros_acidentes": sin_acid.get("possui_registro", "indisponivel"),
        "parecer": parecer_obj.get("parecer", ""),   # "favoravel"|"desfavoravel"|"alerta"
        "parecer_detalhes": {
            "vistorias_negadas": detalhes_parecer.get("registro_vistorias_negadas", ""),
            "frota_locadora": detalhes_parecer.get("registro_frota_locadora", ""),
            "indicios_acidentes": detalhes_parecer.get("registro_indicios_acidentes", ""),
            "veiculo_importado": detalhes_parecer.get("registro_veiculo_importado", ""),
        },
        "remarketing": {
            "possui_registro": remarketing.get("possui_registro", "nao"),
            "registros": [
                {
                    "item": r.get("item", ""),
                    "organizador": r.get("organizador", ""),
                    "data": r.get("data_evento", ""),
                    "cond_geral": r.get("condicao_geral_veiculo", ""),
                    "cond_motor": r.get("condicao_motor", ""),
                    "cond_cambio": r.get("condicao_cambio", ""),
                }
                for r in rem_registros
            ],
            "fotos": remarketing.get("fotos", []),
        },
        "ia_danos": {
            "situacao": ia.get("situacao_analise", ""),
            "danos": ia.get("possiveis_dados", []) or [],
            "pecas": ia.get("possiveis_pecas_danificadas", []) or [],
            "imagens": ia.get("imagens", []) or [],
        },
        "_raw": raw,
    }


def _parse_proprietario(raw: dict) -> dict:
    p = raw.get("dados", {}).get("proprietario_atual", {})
    return {
        "fonte": "consultarplaca/proprietario",
        "nome": p.get("nome", ""),
        "documento": p.get("documento", ""),    # já mascarado pela API
        "tipo_documento": p.get("tipo_documento", ""),
        "_raw": raw,
    }


def _parse_renainf(raw: dict) -> dict:
    reg = raw.get("dados", {}).get("registro_debitos_por_infracoes_renainf", {})
    inf = reg.get("infracoes_renainf", {})
    possui = inf.get("possui_infracoes", "nao")
    infracoes = inf.get("infracoes", []) or []

    parsed = []
    for i in infracoes:
        d = i.get("dados_infracao", {})
        a = i.get("aplicacao", {})
        e = i.get("eventos", {})
        parsed.append({
            "infracao": d.get("infracao", ""),
            "auto": d.get("numero_auto_infracao", ""),
            "valor": d.get("valor_aplicado", ""),
            "orgao": d.get("orgao_autuador", ""),
            "tipo_auto": d.get("tipo_auto_infracao", ""),
            "local": d.get("local_infracao", ""),
            "municipio": d.get("municipio", ""),
            "data_infracao": e.get("data_hora_infracao", ""),
            "data_notificacao": e.get("data_notificacao", ""),
        })

    return {
        "fonte": "consultarplaca/renainf",
        "possui_infracoes": possui,    # "sim" | "nao"
        "infracoes": parsed,
        "_raw": raw,
    }
