#!/usr/bin/env python3
"""
consulta-veicular — Consulta de histórico veicular por placa (Brasil)
Base URL: https://api.consultarplaca.com.br/v2
Docs:     https://docs.consultarplaca.com.br/

Uso:
  python lookup.py <PLACA> [opções]

Exemplos:
  python lookup.py AAA0000               # placa de teste (sem consumir créditos)
  python lookup.py BBJ1A73               # básico + roubo + gravame + sinistro
  python lookup.py BBJ1A73 --leilao      # + histórico de leilão detalhado
  python lookup.py BBJ1A73 --proprietario
  python lookup.py BBJ1A73 --renainf     # + infrações RENAINF
  python lookup.py BBJ1A73 --full        # tudo
  python lookup.py BBJ1A73 --json        # salva resultado em JSON
"""

import argparse
import sys
import re
import datetime
from dotenv import load_dotenv

load_dotenv()

from client import ConsultarPlacaClient, ConsultarPlacaError
import report


def _validar_placa(placa: str) -> str:
    clean = re.sub(r"[^A-Z0-9]", "", placa.upper())
    if not re.match(r"^[A-Z]{3}\d{4}$|^[A-Z]{3}\d[A-Z]\d{2}$", clean):
        print(f"Erro: placa inválida '{placa}'. Use ABC1234 ou ABC1D23.")
        sys.exit(1)
    return clean


def _chamar(client, metodo, placa, label):
    """Chama um método do client e trata erros sem abortar o script."""
    from rich.console import Console
    c = Console()
    c.print(f"[dim]  → {label}...[/dim]")
    try:
        return getattr(client, metodo)(placa)
    except ConsultarPlacaError as e:
        c.print(f"[red]  ✗ {label}: {e}[/red]")
        return {"erro": str(e)}
    except ValueError as e:
        c.print(f"[red]  ✗ {label}: {e}[/red]")
        return {"erro": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Consulta histórico veicular por placa (BR)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("placa", help="Placa (ex: BBJ1A73, ABC-1234). Use AAA0000 para teste.")
    parser.add_argument("--leilao", action="store_true",
                        help="Histórico de leilão Prime (classificação A-D, IA danos, remarketing)")
    parser.add_argument("--proprietario", action="store_true",
                        help="Proprietário atual")
    parser.add_argument("--renainf", action="store_true",
                        help="Infrações RENAINF com valores")
    parser.add_argument("--full", action="store_true",
                        help="Tudo: básico + roubo + gravame + sinistro + leilão + proprietário + RENAINF")
    parser.add_argument("--json", action="store_true",
                        help="Salva resultado em <PLACA>_<timestamp>.json")
    parser.add_argument("--md", action="store_true",
                        help="Salva resultado em <PLACA>_<timestamp>.md (Markdown)")
    parser.add_argument("--pdf", action="store_true",
                        help="Salva resultado em <PLACA>_<timestamp>.pdf (requer fpdf2)")
    args = parser.parse_args()

    placa = _validar_placa(args.placa)

    if args.full:
        args.leilao = True
        args.proprietario = True
        args.renainf = True

    # ── Inicializa client ─────────────────────────────────────────────────────
    try:
        client = ConsultarPlacaClient()
    except ConsultarPlacaError as e:
        print(f"\nErro de configuração: {e}")
        print("\nVerifique seu .env:")
        print("  CONSULTARPLACA_EMAIL=seu@email.com")
        print("  CONSULTARPLACA_API_KEY=sua_chave")
        print("\nObtenha a chave em: consultarplaca.com.br → Minha Conta → API → Gerar API KEY")
        sys.exit(1)

    from rich.console import Console
    Console().print(f"\n[bold]Consultando placa:[/bold] [cyan]{placa}[/cyan]\n")

    # ── Camada padrão ─────────────────────────────────────────────────────────
    basico      = _chamar(client, "dados_basicos", placa, "Dados básicos (cadastro)")
    roubo_furto = _chamar(client, "roubo_furto",   placa, "Histórico roubo/furto")
    gravame     = _chamar(client, "gravame",        placa, "Gravame / alienação fiduciária")
    sinistro    = _chamar(client, "sinistro",       placa, "Sinistro com perda total")

    # ── Camadas opcionais ─────────────────────────────────────────────────────
    leilao      = _chamar(client, "leilao",       placa, "Leilão Prime (pode demorar)") if args.leilao      else None
    proprietario= _chamar(client, "proprietario", placa, "Proprietário atual")          if args.proprietario else None
    renainf_r   = _chamar(client, "renainf",      placa, "Infrações RENAINF")           if args.renainf      else None

    # ── Relatório ─────────────────────────────────────────────────────────────
    report.imprimir_relatorio(
        placa,
        basico=basico,
        roubo_furto=roubo_furto,
        gravame=gravame,
        sinistro=sinistro,
        leilao=leilao,
        proprietario=proprietario,
        renainf=renainf_r,
    )

    # ── Exportar ──────────────────────────────────────────────────────────────
    resultados = {
        "basico": basico,
        "roubo_furto": roubo_furto,
        "gravame": gravame,
        "sinistro": sinistro,
        "leilao": leilao,
        "proprietario": proprietario,
        "renainf": renainf_r,
    }

    if args.json:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report.salvar_json(placa, resultados, f"{placa}_{ts}.json")

    if args.md:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report.salvar_markdown(placa, resultados, f"{placa}_{ts}.md")

    if args.pdf:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report.salvar_pdf(placa, resultados, f"{placa}_{ts}.pdf")


if __name__ == "__main__":
    main()
