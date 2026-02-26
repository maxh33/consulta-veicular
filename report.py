"""
Formatação do relatório veicular — terminal (Rich) e JSON.
"""

import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

console = Console()

SEGURADORAS = (
    "SEGURO", "SEGUROS", "INSURANCE", "BRADESCO", "PORTO SEGURO",
    "LIBERTY", "ALLIANZ", "MAPFRE", "TOKIO", "ZURICH", "SULAMÉRICA",
    "AXA", "HDI", "SOMPO", "ITAU", "SANTANDER AUTO",
)

CLASSIFICACAO_LEILAO = {
    "A": ("Batida leve / dano estético", "yellow"),
    "B": ("Batida moderada", "yellow"),
    "C": ("Batida grave / possível perda total", "red"),
    "D": ("Perda total confirmada", "red"),
    "N": ("Sem classificação registrada", "dim"),
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _ok(val: str) -> Text:
    return Text(f"{val} ✅", style="green")

def _warn(val: str, critico: bool = False) -> Text:
    style = "bold red" if critico else "yellow"
    sufixo = " ⚠️  ALERTA CRÍTICO" if critico else " ⚠️"
    return Text(f"{val}{sufixo}", style=style)

def _na() -> Text:
    return Text("indisponível", style="dim")

def _status_possui(val: str, *, bom_se="nao") -> Text:
    """Para campos possui_registro / possui_gravame — verde se ausente."""
    v = str(val).lower().strip()
    if v == bom_se:
        return _ok("NADA CONSTA")
    if v == "sim":
        return _warn("CONSTA")
    return _na()

def _to_float(val) -> float:
    s = str(val or "0").strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _fmt_moeda(val) -> str:
    s = str(val or "").strip()
    if not s or s == "0":
        return "R$ 0,00"
    if s.startswith("R$"):
        return s
    return f"R$ {_to_float(s):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _simples(t: Table, label: str, valor: str, ok_valor: str | None = None) -> None:
    """Adiciona linha à tabela. Realça em verde se valor == ok_valor."""
    if ok_valor and str(valor).strip().upper() == ok_valor.upper():
        t.add_row(label, _ok(valor))
    elif valor:
        t.add_row(label, valor)
    else:
        t.add_row(label, Text("—", style="dim"))


# ─── Seções ───────────────────────────────────────────────────────────────────

def _secao_dados_veiculo(b: dict) -> None:
    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    t.add_column("", style="bold cyan", width=22)
    t.add_column("")

    marca_modelo = " / ".join(filter(None, [b.get("marca"), b.get("modelo"), b.get("sub_segmento")]))
    ano = f"{b.get('ano_fabricacao', '?')} / {b.get('ano_modelo', '?')}"
    municipio = " — ".join(filter(None, [b.get("municipio"), b.get("uf")]))

    t.add_row("Marca / Modelo", marca_modelo or "—")
    t.add_row("Ano Fab / Modelo", ano)
    t.add_row("Cor", b.get("cor") or "—")
    t.add_row("Combustível", b.get("combustivel") or "—")
    t.add_row("Segmento", b.get("segmento") or "—")
    t.add_row("Procedência", b.get("procedencia") or "—")
    t.add_row("Chassi", b.get("chassi") or "—")
    t.add_row("Motor", b.get("numero_motor") or "—")
    if b.get("numero_caixa_cambio"):
        t.add_row("Câmbio", b.get("numero_caixa_cambio"))
    if b.get("potencia"):
        t.add_row("Potência / Cilind.", f"{b.get('potencia')} CV / {b.get('cilindradas', '—')}")
    if municipio:
        t.add_row("Município", municipio)

    console.print(Panel(t, title="[bold]DADOS DO VEÍCULO[/bold]", border_style="blue"))


def _secao_roubo_furto(r: dict) -> None:
    possui = r.get("possui_registro", "indisponivel")
    registros = r.get("registros", [])

    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    t.add_column("", style="bold cyan", width=22)
    t.add_column("")
    t.add_row("Status", _status_possui(possui))

    if possui == "sim" and registros:
        for i, reg in enumerate(registros, 1):
            t.add_row(
                f"Ocorrência #{i}",
                Text(
                    f"BO {reg.get('boletim_ocorrencia','?')} | "
                    f"{reg.get('data','?')} | "
                    f"{reg.get('tipo','?')} | "
                    f"UF: {reg.get('uf','?')}",
                    style="bold red",
                ),
            )

    border = "red" if possui == "sim" else "green"
    console.print(Panel(t, title="[bold]ROUBO / FURTO[/bold]", border_style=border))


def _secao_gravame(g: dict) -> None:
    possui = g.get("possui_gravame", "indisponivel")

    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    t.add_column("", style="bold cyan", width=22)
    t.add_column("")
    t.add_row("Gravame / Alienação", _status_possui(possui))

    if possui == "sim":
        t.add_row("Agente Financeiro", Text(g.get("agente_financeiro", "—"), style="yellow"))
        if g.get("cnpj_agente"):
            t.add_row("CNPJ", g.get("cnpj_agente"))
        if g.get("data_registro"):
            t.add_row("Data Registro", g.get("data_registro"))
        if g.get("situacao"):
            t.add_row("Situação", g.get("situacao"))

    border = "yellow" if possui == "sim" else "green"
    console.print(Panel(t, title="[bold]GRAVAME / ALIENAÇÃO FIDUCIÁRIA[/bold]", border_style=border))


def _secao_sinistro(s: dict) -> None:
    possui = s.get("possui_registro", "indisponivel")

    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    t.add_column("", style="bold cyan", width=22)
    t.add_column("")
    t.add_row("Sinistro com Perda Total", _status_possui(possui))
    if possui == "sim" and s.get("descricao"):
        t.add_row("Descrição", Text(s.get("descricao", ""), style="bold red"))

    border = "red" if possui == "sim" else "green"
    console.print(Panel(t, title="[bold]SINISTRO COM PERDA TOTAL[/bold]", border_style=border))


def _secao_leilao(l: dict) -> None:
    possui = l.get("possui_registro", "indisponivel")
    classificacao = l.get("classificacao", "")
    leiloes = l.get("leiloes", [])
    parecer = l.get("parecer", "")
    det = l.get("parecer_detalhes", {})
    remarketing = l.get("remarketing", {})
    ia = l.get("ia_danos", {})

    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    t.add_column("", style="bold cyan", width=22)
    t.add_column("")
    t.add_row("Registro de Leilão", _status_possui(possui))

    if possui == "sim":
        # Classificação
        if classificacao and classificacao in CLASSIFICACAO_LEILAO:
            descr, cor = CLASSIFICACAO_LEILAO[classificacao]
            t.add_row("Classificação", Text(f"{classificacao} — {descr}", style=f"bold {cor}"))
        elif classificacao:
            t.add_row("Classificação", classificacao)

        # Parecer técnico
        if parecer:
            cor_parecer = {"favoravel": "green", "desfavoravel": "red", "alerta": "yellow"}.get(parecer, "")
            t.add_row("Parecer Técnico", Text(parecer.upper(), style=f"bold {cor_parecer}"))
        for campo, label in [
            ("vistorias_negadas", "Vistorias Negadas"),
            ("frota_locadora", "Frota Locadora"),
            ("indicios_acidentes", "Indícios Acidentes"),
        ]:
            val = det.get(campo, "")
            if val == "sim":
                t.add_row(f"  {label}", _warn("SIM"))
            elif val == "nao":
                t.add_row(f"  {label}", _ok("NÃO"))

        # Sinistros/acidentes (flag incluído na resposta de leilão)
        sin = l.get("sinistros_acidentes", "")
        if sin:
            t.add_row("Sinistros/Acidentes", _status_possui(sin))

    console.print(Panel(
        t,
        title=("[bold red]LEILÃO ⚠️  REGISTRO ENCONTRADO[/bold red]"
               if possui == "sim"
               else "[bold]LEILÃO[/bold]"),
        border_style="red" if possui == "sim" else "green",
    ))

    # Registros individuais de leilão
    if leiloes:
        tl = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
        tl.add_column("#", style="dim", width=3)
        tl.add_column("Comitente", style="bold")
        tl.add_column("Data")
        tl.add_column("Lote")
        tl.add_column("Classi.")
        tl.add_column("Segmento")

        for i, reg in enumerate(leiloes, 1):
            comitente = reg.get("comitente", "—")
            comitente_txt = Text(comitente, style="bold red")
            if any(s in comitente.upper() for s in SEGURADORAS):
                comitente_txt = Text(f"{comitente} ← seguradora", style="bold red")

            tl.add_row(
                str(i),
                comitente_txt,
                reg.get("data_leilao", "—"),
                reg.get("lote", "—"),
                reg.get("classificacao", "—"),
                reg.get("segmento", "—"),
            )
        console.print(Panel(tl, title="[bold red]Registros de Leilão[/bold red]", border_style="red"))

    # Remarketing
    if remarketing.get("possui_registro") == "sim" and remarketing.get("registros"):
        tr = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
        tr.add_column("Data")
        tr.add_column("Organizador")
        tr.add_column("Item")
        tr.add_column("Cond. Geral")
        tr.add_column("Motor")
        tr.add_column("Câmbio")
        for r in remarketing["registros"]:
            tr.add_row(r.get("data","—"), r.get("organizador","—"), r.get("item","—"),
                       r.get("cond_geral","—"), r.get("cond_motor","—"), r.get("cond_cambio","—"))
        console.print(Panel(tr, title="[bold]Remarketing[/bold]", border_style="yellow"))

    # IA — danos detectados
    if ia.get("situacao") == "concluido" and (ia.get("danos") or ia.get("pecas")):
        tid = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
        tid.add_column("Local / Peça")
        tid.add_column("Probabilidade", justify="right")
        for d in ia.get("danos", []):
            tid.add_row(f"{d.get('local','')} — {d.get('descricao','')}", f"{d.get('probabilidade',0):.0f}%")
        for p in ia.get("pecas", []):
            tid.add_row(p.get("descricao", ""), f"{p.get('probabilidade',0):.0f}%")
        console.print(Panel(tid, title="[bold yellow]Danos Detectados por IA[/bold yellow]", border_style="yellow"))


def _secao_proprietario(p: dict) -> None:
    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    t.add_column("", style="bold cyan", width=20)
    t.add_column("")
    t.add_row("Nome / Razão Social", p.get("nome") or "—")
    if p.get("documento"):
        t.add_row("Documento", p.get("documento"))   # já mascarado pela API
    if p.get("tipo_documento"):
        t.add_row("Tipo", p.get("tipo_documento"))
    console.print(Panel(t, title="[bold]PROPRIETÁRIO ATUAL[/bold]", border_style="blue"))


def _secao_renainf(r: dict) -> None:
    possui = r.get("possui_infracoes", "nao")
    infracoes = r.get("infracoes", [])

    if possui != "sim" or not infracoes:
        t = Table(box=box.SIMPLE, show_header=False)
        t.add_column("")
        t.add_row(_ok("NADA CONSTA"))
        console.print(Panel(t, title="[bold]INFRAÇÕES RENAINF[/bold]", border_style="green"))
        return

    total = sum(
        _to_float(i.get("valor", ""))
        for i in infracoes
        if i.get("valor") not in (None, "", "0")
    )

    t = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
    t.add_column("Infração", max_width=40)
    t.add_column("Valor", justify="right")
    t.add_column("Órgão")
    t.add_column("Data")
    t.add_column("Local")

    for i in infracoes:
        t.add_row(
            i.get("infracao", "—"),
            _fmt_moeda(i.get("valor", "")),
            i.get("orgao", "—"),
            i.get("data_infracao", "—"),
            i.get("local", i.get("municipio", "—")),
        )

    titulo = f"[bold yellow]INFRAÇÕES RENAINF ⚠️  {len(infracoes)} registro(s) — Total: {_fmt_moeda(total)}[/bold yellow]"
    console.print(Panel(t, title=titulo, border_style="yellow"))


# ─── Entry points ─────────────────────────────────────────────────────────────

def imprimir_relatorio(
    placa: str,
    basico: dict | None = None,
    roubo_furto: dict | None = None,
    gravame: dict | None = None,
    sinistro: dict | None = None,
    leilao: dict | None = None,
    proprietario: dict | None = None,
    renainf: dict | None = None,
) -> None:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")
    console.print()
    console.rule(f"[bold white]RELATÓRIO VEICULAR — {placa.upper()} — {agora}[/bold white]")
    console.print()

    def _render(dados, secao_fn, label):
        if dados is None:
            return
        if "erro" in dados:
            console.print(f"[red]{label}: {dados['erro']}[/red]")
        else:
            secao_fn(dados)

    _render(basico, _secao_dados_veiculo, "Dados básicos")
    _render(roubo_furto, _secao_roubo_furto, "Roubo/Furto")
    _render(gravame, _secao_gravame, "Gravame")
    _render(sinistro, _secao_sinistro, "Sinistro")
    _render(leilao, _secao_leilao, "Leilão")
    _render(proprietario, _secao_proprietario, "Proprietário")
    _render(renainf, _secao_renainf, "RENAINF")

    console.print()
    console.rule()
    console.print()


def salvar_markdown(placa: str, resultados: dict, caminho: str) -> None:
    """Salva relatório em formato Markdown."""
    lines = []
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines += [f"# Relatório Veicular — {placa.upper()}", "",
              f"**Consulta em:** {agora}", "", "---", ""]

    # Dados básicos
    b = resultados.get("basico")
    if b is not None:
        lines.append("## Dados do Veículo\n")
        if "erro" in b:
            lines.append(f"> Erro: {b['erro']}")
        else:
            marca_modelo = " / ".join(filter(None, [b.get("marca"), b.get("modelo"), b.get("sub_segmento")]))
            lines.append(f"- **Marca / Modelo:** {marca_modelo or '—'}")
            lines.append(f"- **Ano Fab / Modelo:** {b.get('ano_fabricacao','?')} / {b.get('ano_modelo','?')}")
            for campo, label in [("cor","Cor"), ("combustivel","Combustível"), ("segmento","Segmento"),
                                  ("procedencia","Procedência"), ("chassi","Chassi"), ("numero_motor","Motor")]:
                if b.get(campo):
                    lines.append(f"- **{label}:** {b[campo]}")
            if b.get("numero_caixa_cambio"):
                lines.append(f"- **Câmbio:** {b['numero_caixa_cambio']}")
            if b.get("potencia"):
                lines.append(f"- **Potência / Cilind.:** {b['potencia']} CV / {b.get('cilindradas','—')}")
            municipio = " — ".join(filter(None, [b.get("municipio"), b.get("uf")]))
            if municipio:
                lines.append(f"- **Município:** {municipio}")
        lines.append("")

    # Roubo/Furto
    r = resultados.get("roubo_furto")
    if r is not None:
        lines.append("## Roubo / Furto\n")
        if "erro" in r:
            lines.append(f"> Erro: {r['erro']}")
        else:
            possui = r.get("possui_registro", "indisponivel")
            status = "NADA CONSTA ✅" if possui == "nao" else ("CONSTA ⚠️" if possui == "sim" else "indisponível")
            lines.append(f"- **Status:** {status}")
            if possui == "sim":
                for i, reg in enumerate(r.get("registros", []), 1):
                    lines.append(
                        f"- **Ocorrência #{i}:** BO {reg.get('boletim_ocorrencia','?')} | "
                        f"{reg.get('data','?')} | {reg.get('tipo','?')} | UF: {reg.get('uf','?')}"
                    )
        lines.append("")

    # Gravame
    g = resultados.get("gravame")
    if g is not None:
        lines.append("## Gravame / Alienação Fiduciária\n")
        if "erro" in g:
            lines.append(f"> Erro: {g['erro']}")
        else:
            possui = g.get("possui_gravame", "indisponivel")
            status = "NADA CONSTA ✅" if possui == "nao" else ("CONSTA ⚠️" if possui == "sim" else "indisponível")
            lines.append(f"- **Gravame / Alienação:** {status}")
            if possui == "sim":
                lines.append(f"- **Agente Financeiro:** {g.get('agente_financeiro','—')}")
                if g.get("cnpj_agente"): lines.append(f"- **CNPJ:** {g['cnpj_agente']}")
                if g.get("data_registro"): lines.append(f"- **Data Registro:** {g['data_registro']}")
                if g.get("situacao"): lines.append(f"- **Situação:** {g['situacao']}")
        lines.append("")

    # Sinistro
    s = resultados.get("sinistro")
    if s is not None:
        lines.append("## Sinistro com Perda Total\n")
        if "erro" in s:
            lines.append(f"> Erro: {s['erro']}")
        else:
            possui = s.get("possui_registro", "indisponivel")
            status = "NADA CONSTA ✅" if possui == "nao" else ("CONSTA ⚠️" if possui == "sim" else "indisponível")
            lines.append(f"- **Sinistro com Perda Total:** {status}")
            if possui == "sim" and s.get("descricao"):
                lines.append(f"- **Descrição:** {s['descricao']}")
        lines.append("")

    # Leilão
    l = resultados.get("leilao")
    if l is not None:
        lines.append("## Leilão\n")
        if "erro" in l:
            lines.append(f"> Erro: {l['erro']}")
        else:
            possui = l.get("possui_registro", "indisponivel")
            status = "NADA CONSTA ✅" if possui == "nao" else ("CONSTA ⚠️  REGISTRO ENCONTRADO" if possui == "sim" else "indisponível")
            lines.append(f"- **Registro de Leilão:** {status}")
            if possui == "sim":
                classificacao = l.get("classificacao", "")
                if classificacao and classificacao in CLASSIFICACAO_LEILAO:
                    descr, _ = CLASSIFICACAO_LEILAO[classificacao]
                    lines.append(f"- **Classificação:** {classificacao} — {descr}")
                elif classificacao:
                    lines.append(f"- **Classificação:** {classificacao}")
                parecer = l.get("parecer", "")
                if parecer:
                    lines.append(f"- **Parecer Técnico:** {parecer.upper()}")
                det = l.get("parecer_detalhes", {})
                for campo, label in [("vistorias_negadas", "Vistorias Negadas"),
                                      ("frota_locadora", "Frota Locadora"),
                                      ("indicios_acidentes", "Indícios Acidentes")]:
                    val = det.get(campo, "")
                    if val:
                        lines.append(f"- **{label}:** {val.upper()}")
                sin = l.get("sinistros_acidentes", "")
                if sin:
                    lines.append(f"- **Sinistros/Acidentes:** {sin}")

            leiloes = l.get("leiloes", [])
            if leiloes:
                lines += ["", "### Registros de Leilão", "",
                          "| # | Comitente | Data | Lote | Classi. | Segmento |",
                          "|---|-----------|------|------|---------|----------|"]
                for i, reg in enumerate(leiloes, 1):
                    comitente = reg.get("comitente", "—")
                    if any(seg in comitente.upper() for seg in SEGURADORAS):
                        comitente = f"{comitente} ← seguradora"
                    lines.append(
                        f"| {i} | {comitente} | {reg.get('data_leilao','—')} | "
                        f"{reg.get('lote','—')} | {reg.get('classificacao','—')} | {reg.get('segmento','—')} |"
                    )

            remarketing = l.get("remarketing", {})
            if remarketing.get("possui_registro") == "sim" and remarketing.get("registros"):
                lines += ["", "### Remarketing", "",
                          "| Data | Organizador | Item | Cond. Geral | Motor | Câmbio |",
                          "|------|-------------|------|-------------|-------|--------|"]
                for reg in remarketing["registros"]:
                    lines.append(
                        f"| {reg.get('data','—')} | {reg.get('organizador','—')} | "
                        f"{reg.get('item','—')} | {reg.get('cond_geral','—')} | "
                        f"{reg.get('cond_motor','—')} | {reg.get('cond_cambio','—')} |"
                    )

            ia = l.get("ia_danos", {})
            if ia.get("situacao") == "concluido" and (ia.get("danos") or ia.get("pecas")):
                lines += ["", "### Danos Detectados por IA", "",
                          "| Local / Peça | Probabilidade |",
                          "|--------------|---------------|"]
                for d in ia.get("danos", []):
                    prob = _to_float(d.get("probabilidade", 0))
                    lines.append(f"| {d.get('local','')} — {d.get('descricao','')} | {prob:.0f}% |")
                for p in ia.get("pecas", []):
                    prob = _to_float(p.get("probabilidade", 0))
                    lines.append(f"| {p.get('descricao','')} | {prob:.0f}% |")
        lines.append("")

    # Proprietário
    p = resultados.get("proprietario")
    if p is not None:
        lines.append("## Proprietário Atual\n")
        if "erro" in p:
            lines.append(f"> Erro: {p['erro']}")
        else:
            lines.append(f"- **Nome / Razão Social:** {p.get('nome') or '—'}")
            if p.get("documento"): lines.append(f"- **Documento:** {p['documento']}")
            if p.get("tipo_documento"): lines.append(f"- **Tipo:** {p['tipo_documento']}")
        lines.append("")

    # RENAINF
    rn = resultados.get("renainf")
    if rn is not None:
        lines.append("## Infrações RENAINF\n")
        if "erro" in rn:
            lines.append(f"> Erro: {rn['erro']}")
        else:
            possui = rn.get("possui_infracoes", "nao")
            infracoes = rn.get("infracoes", [])
            if possui != "sim" or not infracoes:
                lines.append("NADA CONSTA ✅")
            else:
                total = sum(_to_float(i.get("valor", "")) for i in infracoes
                            if i.get("valor") not in (None, "", "0"))
                lines.append(f"**{len(infracoes)} infração(ões) — Total: {_fmt_moeda(total)}** ⚠️")
                lines += ["",
                          "| Infração | Valor | Órgão | Data | Local |",
                          "|---------|-------|-------|------|-------|"]
                for i in infracoes:
                    lines.append(
                        f"| {i.get('infracao','—')} | {_fmt_moeda(i.get('valor',''))} | "
                        f"{i.get('orgao','—')} | {i.get('data_infracao','—')} | "
                        f"{i.get('local', i.get('municipio','—'))} |"
                    )
        lines.append("")

    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    console.print(f"[green]Markdown salvo em:[/green] {caminho}")


def salvar_pdf(placa: str, resultados: dict, caminho: str) -> None:
    """Salva relatório em PDF usando fpdf2."""
    try:
        from fpdf import FPDF
    except ImportError:
        console.print("[red]fpdf2 não instalado. Execute: pip install fpdf2[/red]")
        return

    W = 180  # largura útil em mm (A4 = 210, margens 15 cada lado)

    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    agora = datetime.now().strftime("%Y-%m-%d %H:%M")

    def _s(v) -> str:
        """Garante string Latin-1 segura para fontes nativas do PDF."""
        s = (str(v or "")
             .replace("\u2014", "-")
             .replace("\u2013", "-")
             .replace("\u2190", "<-")
             .replace("\u2026", "..."))
        return s.encode("latin-1", errors="replace").decode("latin-1")

    def hdr(title, alert=False):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        if alert:
            pdf.set_fill_color(200, 50, 50)
        else:
            pdf.set_fill_color(50, 90, 160)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(W, 8, _s(title), fill=True)
        pdf.ln()
        pdf.set_text_color(0, 0, 0)
        pdf.ln(1)

    def _fit(txt, max_w):
        """Truncate txt to fit within max_w mm at current font, adding '.' if cut."""
        if pdf.get_string_width(txt) <= max_w:
            return txt
        while txt and pdf.get_string_width(txt + ".") > max_w:
            txt = txt[:-1]
        return txt + "."

    def kv(label, value, alert=False):
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(55, 6, _s(label) + ":")
        pdf.set_font("Helvetica", "", 9)
        if alert:
            pdf.set_text_color(180, 0, 0)
        pdf.cell(W - 55, 6, _fit(_s(str(value or "-")), W - 55 - 2))
        pdf.set_text_color(0, 0, 0)
        pdf.ln()

    def th(cols, widths):
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(210, 220, 240)
        for col, w in zip(cols, widths):
            pdf.cell(w, 6, _s(col), border=1, fill=True)
        pdf.ln()

    def tr(cells, widths, alert=False):
        pdf.set_font("Helvetica", "", 8)
        if alert:
            pdf.set_text_color(180, 0, 0)
        for cell, w in zip(cells, widths):
            pdf.cell(w, 5, _fit(_s(str(cell or "-")), w - 2), border=1)
        pdf.ln()
        pdf.set_text_color(0, 0, 0)

    # Título
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_fill_color(30, 60, 120)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(W, 12, f"RELATORIO VEICULAR - {placa.upper()}", fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(W, 6, f"Consulta em: {agora}", align="C")
    pdf.ln(8)

    # Dados básicos
    b = resultados.get("basico")
    if b is not None:
        hdr("DADOS DO VEICULO")
        if "erro" in b:
            kv("Erro", b["erro"], alert=True)
        else:
            marca_modelo = " / ".join(filter(None, [b.get("marca"), b.get("modelo"), b.get("sub_segmento")]))
            kv("Marca / Modelo", marca_modelo or "-")
            kv("Ano Fab / Modelo", f"{b.get('ano_fabricacao','?')} / {b.get('ano_modelo','?')}")
            if b.get("cor"): kv("Cor", b["cor"])
            if b.get("combustivel"): kv("Combustivel", b["combustivel"])
            if b.get("segmento"): kv("Segmento", b["segmento"])
            if b.get("procedencia"): kv("Procedencia", b["procedencia"])
            if b.get("chassi"): kv("Chassi", b["chassi"])
            if b.get("numero_motor"): kv("Motor", b["numero_motor"])
            if b.get("numero_caixa_cambio"): kv("Cambio", b["numero_caixa_cambio"])
            if b.get("potencia"):
                kv("Potencia / Cilind.", f"{b['potencia']} CV / {b.get('cilindradas','-')}")
            municipio = " - ".join(filter(None, [b.get("municipio"), b.get("uf")]))
            if municipio: kv("Municipio", municipio)

    # Roubo/Furto
    r = resultados.get("roubo_furto")
    if r is not None:
        possui = r.get("possui_registro", "indisponivel")
        hdr("ROUBO / FURTO", alert=(possui == "sim"))
        if "erro" in r:
            kv("Erro", r["erro"], alert=True)
        else:
            status = "NADA CONSTA" if possui == "nao" else ("CONSTA - ALERTA" if possui == "sim" else "indisponivel")
            kv("Status", status, alert=(possui == "sim"))
            if possui == "sim":
                for i, reg in enumerate(r.get("registros", []), 1):
                    kv(f"Ocorrencia #{i}",
                       f"BO {reg.get('boletim_ocorrencia','?')} | {reg.get('data','?')} | {reg.get('tipo','?')} | UF: {reg.get('uf','?')}",
                       alert=True)

    # Gravame
    g = resultados.get("gravame")
    if g is not None:
        possui = g.get("possui_gravame", "indisponivel")
        hdr("GRAVAME / ALIENACAO FIDUCIARIA", alert=(possui == "sim"))
        if "erro" in g:
            kv("Erro", g["erro"], alert=True)
        else:
            status = "NADA CONSTA" if possui == "nao" else ("CONSTA - ALERTA" if possui == "sim" else "indisponivel")
            kv("Gravame / Alienacao", status, alert=(possui == "sim"))
            if possui == "sim":
                kv("Agente Financeiro", g.get("agente_financeiro", "-"), alert=True)
                if g.get("cnpj_agente"): kv("CNPJ", g["cnpj_agente"])
                if g.get("data_registro"): kv("Data Registro", g["data_registro"])
                if g.get("situacao"): kv("Situacao", g["situacao"])

    # Sinistro
    s = resultados.get("sinistro")
    if s is not None:
        possui = s.get("possui_registro", "indisponivel")
        hdr("SINISTRO COM PERDA TOTAL", alert=(possui == "sim"))
        if "erro" in s:
            kv("Erro", s["erro"], alert=True)
        else:
            status = "NADA CONSTA" if possui == "nao" else ("CONSTA - ALERTA" if possui == "sim" else "indisponivel")
            kv("Sinistro com Perda Total", status, alert=(possui == "sim"))
            if possui == "sim" and s.get("descricao"):
                kv("Descricao", s["descricao"], alert=True)

    # Leilão
    l = resultados.get("leilao")
    if l is not None:
        possui = l.get("possui_registro", "indisponivel")
        hdr("LEILAO" + (" - REGISTRO ENCONTRADO" if possui == "sim" else ""), alert=(possui == "sim"))
        if "erro" in l:
            kv("Erro", l["erro"], alert=True)
        else:
            status = "NADA CONSTA" if possui == "nao" else ("CONSTA - ALERTA" if possui == "sim" else "indisponivel")
            kv("Registro de Leilao", status, alert=(possui == "sim"))
            if possui == "sim":
                classificacao = l.get("classificacao", "")
                if classificacao and classificacao in CLASSIFICACAO_LEILAO:
                    descr, _ = CLASSIFICACAO_LEILAO[classificacao]
                    kv("Classificacao", f"{classificacao} - {descr}", alert=True)
                elif classificacao:
                    kv("Classificacao", classificacao)
                parecer = l.get("parecer", "")
                if parecer:
                    kv("Parecer Tecnico", parecer.upper(), alert=(parecer == "desfavoravel"))
                det = l.get("parecer_detalhes", {})
                for campo, label in [("vistorias_negadas", "Vistorias Negadas"),
                                      ("frota_locadora", "Frota Locadora"),
                                      ("indicios_acidentes", "Indicios Acidentes")]:
                    val = det.get(campo, "")
                    if val:
                        kv(label, val.upper(), alert=(val == "sim"))

            leiloes = l.get("leiloes", [])
            if leiloes:
                pdf.ln(2)
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(W, 6, "Registros de Leilao:")
                pdf.ln()
                ws = [6, 50, 24, 18, 32, 50]
                th(["#", "Comitente", "Data", "Lote", "Classi.", "Segmento"], ws)
                for i, reg in enumerate(leiloes, 1):
                    comitente = reg.get("comitente", "-")
                    if any(seg in comitente.upper() for seg in SEGURADORAS):
                        comitente = f"{comitente} (seg.)"
                    tr([str(i), comitente, reg.get("data_leilao", "-"),
                        reg.get("lote", "-"), reg.get("classificacao", "-"),
                        reg.get("segmento", "-")], ws, alert=True)

            remarketing = l.get("remarketing", {})
            if remarketing.get("possui_registro") == "sim" and remarketing.get("registros"):
                pdf.ln(2)
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(W, 6, "Remarketing:")
                pdf.ln()
                ws = [22, 48, 32, 30, 24, 24]
                th(["Data", "Organizador", "Item", "Cond. Geral", "Motor", "Cambio"], ws)
                for reg in remarketing["registros"]:
                    tr([reg.get("data", "-"), reg.get("organizador", "-"), reg.get("item", "-"),
                        reg.get("cond_geral", "-"), reg.get("cond_motor", "-"), reg.get("cond_cambio", "-")], ws)

            ia = l.get("ia_danos", {})
            if ia.get("situacao") == "concluido" and (ia.get("danos") or ia.get("pecas")):
                pdf.ln(2)
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(W, 6, "Danos Detectados por IA:")
                pdf.ln()
                ws = [150, 30]
                th(["Local / Peca", "Probabilidade"], ws)
                for d in ia.get("danos", []):
                    prob = _to_float(d.get("probabilidade", 0))
                    tr([f"{d.get('local','')} - {d.get('descricao','')}", f"{prob:.0f}%"], ws, alert=True)
                for p in ia.get("pecas", []):
                    prob = _to_float(p.get("probabilidade", 0))
                    tr([p.get("descricao", ""), f"{prob:.0f}%"], ws, alert=True)

    # Proprietário
    p = resultados.get("proprietario")
    if p is not None:
        hdr("PROPRIETARIO ATUAL")
        if "erro" in p:
            kv("Erro", p["erro"], alert=True)
        else:
            kv("Nome / Razao Social", p.get("nome") or "-")
            if p.get("documento"): kv("Documento", p["documento"])
            if p.get("tipo_documento"): kv("Tipo", p["tipo_documento"])

    # RENAINF
    rn = resultados.get("renainf")
    if rn is not None:
        possui_rn = rn.get("possui_infracoes", "nao")
        infracoes_rn = rn.get("infracoes", []) if "erro" not in rn else []
        hdr("INFRACOES RENAINF", alert=(possui_rn == "sim" and bool(infracoes_rn)))
        if "erro" in rn:
            kv("Erro", rn["erro"], alert=True)
        else:
            if possui_rn != "sim" or not infracoes_rn:
                kv("Status", "NADA CONSTA")
            else:
                total = sum(_to_float(i.get("valor", "")) for i in infracoes_rn
                            if i.get("valor") not in (None, "", "0"))
                kv("Resumo", f"{len(infracoes_rn)} infracao(oes) - Total: {_fmt_moeda(total)}", alert=True)
                ws = [70, 22, 28, 34, 26]
                th(["Infracao", "Valor", "Orgao", "Data/Hora", "Local"], ws)
                for i in infracoes_rn:
                    tr([i.get("infracao", "-"), _fmt_moeda(i.get("valor", "")),
                        i.get("orgao", "-"), i.get("data_infracao", "-"),
                        i.get("local", i.get("municipio", "-"))], ws, alert=True)

    pdf.output(caminho)
    console.print(f"[green]PDF salvo em:[/green] {caminho}")


def salvar_json(placa: str, resultados: dict, caminho: str) -> None:
    """
    Salva todos os resultados em JSON.
    resultados: dict com chaves basico, roubo_furto, gravame, sinistro, leilao, proprietario, renainf
    """
    def _limpar(d):
        if not isinstance(d, dict):
            return d
        return {k: v for k, v in d.items() if k != "_raw"}

    payload = {
        "placa": placa.upper(),
        "consulta_em": datetime.now().isoformat(),
        **{k: _limpar(v) for k, v in resultados.items()},
    }
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    console.print(f"[green]JSON salvo em:[/green] {caminho}")
