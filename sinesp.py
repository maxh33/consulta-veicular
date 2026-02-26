"""
Sinesp Cidadão — consulta gratuita de situação do veículo.

Retorna dados básicos (marca, modelo, cor, chassi) e situação de roubo/furto
usando apenas a placa, sem RENAVAM e sem custo.

ATENÇÃO — Limitações conhecidas:
  - Usa endpoint não-oficial do app móvel (engenharia reversa de SinespCidadao 3.0.2.1)
  - Requer IP brasileiro — conexões de fora do Brasil são bloqueadas pelo servidor
  - Instável: o endpoint pode mudar a qualquer atualização do app
  - Se falhar, use VPN com saída no Brasil

Campos retornados:
  fonte          "sinesp"
  placa          Placa consultada
  situacao       "Em circulação normal" | "Roubado" | "Furtado" | ...
  restricoes     Restrições (texto livre) ou ""
  marca          Fabricante (ex: "VW/VOLKSWAGEN")
  modelo         Modelo (ex: "UP TAKE MCV")
  cor            Cor predominante
  ano_fabricacao Ano de fabricação (string)
  ano_modelo     Ano do modelo (string)
  municipio      Município de emplacamento
  uf             UF do município
  chassi         Número do chassi (parcialmente mascarado)

Uso como módulo:
  from sinesp import consultar
  resultado = consultar("BBJ1A73")
  if "erro" not in resultado:
      print(resultado["situacao"])

Uso como script (requer IP brasileiro ou VPN):
  python sinesp.py BBJ1A73
  python sinesp.py BBJ1A73 --json
"""

import hashlib
import os
import re
import struct
import time
import socket
import requests
from dotenv import load_dotenv

load_dotenv()

# Sinesp endpoint (reverse-engineered, instável — pode mudar com atualizações)
SINESP_URL = "https://cidadao.sinesp.gov.br/sinesp-cidadao/mobile/consultar-placa"

# Headers que imitam o app móvel oficial
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "SinespCidadao / 3.0.2.1 (guroo.com.br)",
    "Host": "cidadao.sinesp.gov.br",
    "Accept": "application/json",
}

# Token estático do app Sinesp — lido do ambiente (.env: SINESP_TOKEN=...)
SECRET = os.getenv("SINESP_TOKEN", "")


def _generate_token(plate: str) -> str:
    """Gera token HMAC necessário para autenticação no Sinesp."""
    plate_clean = plate.upper().replace("-", "")
    date = time.strftime("%Y%m%d%H%M%S")
    msg = f"{plate_clean}{date}{SECRET}"
    return hashlib.sha1(msg.encode()).hexdigest()


def _get_client_ip() -> str:
    """Retorna IP local para o campo obrigatório latitude/longitude."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def consultar(placa: str) -> dict:
    """
    Consulta o Sinesp Cidadão pela placa.

    Args:
        placa: Placa no formato antigo (ABC1234) ou Mercosul (ABC1D23).
              Hífens são ignorados.

    Returns:
        dict com os dados do veículo ou erro.
        Chaves comuns: placa, situacao, restricoes, marca, modelo, cor,
                       ano_fabricacao, ano_modelo, municipio, uf, chassi
    """
    if not SECRET:
        return {"erro": "SINESP_TOKEN não configurado. Adicione ao .env: SINESP_TOKEN=<token>"}

    plate_clean = re.sub(r"[^A-Z0-9]", "", placa.upper())

    if not re.match(r"^[A-Z]{3}\d{4}$|^[A-Z]{3}\d[A-Z]\d{2}$", plate_clean):
        return {"erro": f"Placa inválida: {placa}. Use formato ABC1234 ou ABC1D23."}

    token = _generate_token(plate_clean)
    ip = _get_client_ip()

    payload = {
        "placa": plate_clean,
        "token": token,
        "data": time.strftime("%Y%m%d%H%M%S"),
        "latitude": "0",
        "longitude": "0",
        "ip": ip,
    }

    try:
        resp = requests.post(SINESP_URL, data=payload, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.HTTPError as e:
        return {"erro": f"Sinesp HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except requests.exceptions.ConnectionError:
        return {"erro": "Sinesp: falha de conexão. Verifique sua internet."}
    except requests.exceptions.Timeout:
        return {"erro": "Sinesp: timeout após 15s."}
    except ValueError:
        return {"erro": f"Sinesp: resposta não-JSON. Conteúdo: {resp.text[:200]}"}

    return _normalizar(data)


def _normalizar(raw: dict) -> dict:
    """Normaliza a resposta do Sinesp para um formato consistente."""
    # O Sinesp retorna erros em 'return' ou 'msg'
    if raw.get("return", "").upper() not in ("", "OK"):
        return {"erro": f"Sinesp: {raw.get('return', raw.get('msg', 'Erro desconhecido'))}"}

    # Mapeia campos do Sinesp para nomes legíveis
    return {
        "fonte": "sinesp",
        "placa": raw.get("placa", ""),
        "situacao": raw.get("situacao", ""),
        "restricoes": raw.get("restricoes", ""),
        "marca": raw.get("marca", ""),
        "modelo": raw.get("modelo", ""),
        "cor": raw.get("cor", ""),
        "ano_fabricacao": raw.get("anoFabricacao", ""),
        "ano_modelo": raw.get("anoModelo", ""),
        "municipio": raw.get("municipio", ""),
        "uf": raw.get("uf", ""),
        "chassi": raw.get("chassi", ""),
    }


if __name__ == "__main__":
    import sys
    import json as _json

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Uso: python sinesp.py <PLACA> [--json]")
        print("Exemplo: python sinesp.py BBJ1A73")
        print("         python sinesp.py BBJ1A73 --json")
        print()
        print("Requer IP brasileiro (ou VPN com saída no Brasil).")
        sys.exit(0)

    placa_arg = sys.argv[1]
    as_json = "--json" in sys.argv

    resultado = consultar(placa_arg)

    if as_json:
        print(_json.dumps(resultado, indent=2, ensure_ascii=False))
        sys.exit(1 if "erro" in resultado else 0)

    if "erro" in resultado:
        print(f"Erro: {resultado['erro']}", file=sys.stderr)
        sys.exit(1)

    # Pretty-print
    r = resultado
    print(f"\nPlaca:          {r.get('placa', placa_arg.upper())}")
    print(f"Situação:       {r.get('situacao', '—')}")
    if r.get("restricoes"):
        print(f"Restrições:     {r['restricoes']}")
    print(f"Marca/Modelo:   {r.get('marca', '—')} / {r.get('modelo', '—')}")
    print(f"Cor:            {r.get('cor', '—')}")
    print(f"Ano fab/modelo: {r.get('ano_fabricacao', '—')} / {r.get('ano_modelo', '—')}")
    print(f"Chassi:         {r.get('chassi', '—')}")
    print(f"Município:      {r.get('municipio', '—')} — {r.get('uf', '—')}")
