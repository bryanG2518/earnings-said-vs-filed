"""Brief layout. All numbers are filled by code from computed values."""
from . import fmt
from .validate import DISCLAIMER, validate_brief
from .models import is_verified_sec_source
from urllib.parse import urlparse

GLOSSARY = {
    "en": {
        "Guidance": "The company's own forecast for a future period.",
        "GAAP": "Standard accounting rules; 'adjusted' figures remove items the company treats as unusual.",
        "Free cash flow": "Cash from operations minus capital spending.",
        "Remaining performance obligations": "Contracted revenue not yet recognized; a measure of backlog.",
        "Pre-arranged trading plan (10b5-1)": "A plan set up in advance that schedules an insider's trades.",
        "Tax withholding (Form 4 code F)": "Shares kept back automatically to pay taxes when stock awards vest.",
    },
    "es": {
        "Guía (guidance)": "El pronóstico de la propia empresa para un período futuro.",
        "GAAP": "Normas contables estándar; las cifras 'ajustadas' excluyen partidas que la empresa considera inusuales.",
        "Flujo de caja libre": "Efectivo de operaciones menos inversión en capital.",
        "Obligaciones de desempeño pendientes": "Ingresos contratados aún no reconocidos; una medida de la cartera de pedidos.",
        "Plan de venta preestablecido (10b5-1)": "Un plan acordado con anticipación que programa las operaciones de un directivo.",
        "Retención de impuestos (código F del Form 4)": "Acciones retenidas automáticamente para pagar impuestos cuando se liberan acciones otorgadas.",
    },
}
LABELS = {
    "en": {"changed": "What changed", "findings": "Findings",
           "source": "Source", "conf": "Confidence",
           "not": "What this does not mean", "context": "Context",
           "log": "Source log", "gloss": "Glossary"},
    "es": {"changed": "Qué cambió", "findings": "Hallazgos",
           "source": "Fuente", "conf": "Confianza",
           "not": "Lo que esto no significa", "context": "Contexto",
           "log": "Registro de fuentes", "gloss": "Glosario"},
}


TITLES = {"guidance_delta": "Guidance change", "one_time_items": "One-time items",
          "cash_vs_earnings": "Cash flow vs. earnings",
          "capital_action": "Capital action",
          "income_divergence": "Income line divergence",
          "backlog_vs_revenue": "Backlog vs. revenue",
          "footnote_comparability": "Comparability footnote",
          "insider_activity": "Insider activity", "plan_event": "Trading-plan event",
          "leadership_change": "Leadership change", "macro_driver": "Named macro factor"}


def _cite(s):
    sec = f", {s.section}" if s.section else ""
    if is_verified_sec_source(s):
        return (f"[Form {s.form}, filed {s.filed}{sec}]({s.url}) "
                f"(SEC accession {s.accession})")
    site = urlparse(s.url).netloc or "unknown site"
    return (f"NOT AN SEC FILING: [{site}{sec}]({s.url}), dated {s.filed}. "
            "Verify against the company's filing before relying on it.")


def render(q, findings, lang="en"):
    L = LABELS[lang]
    core = [f for f in findings if f.tier != "context"]
    context = [f for f in findings if f.tier == "context"]
    lines = [f"# {q['company']} ({q['ticker']}) — {q['fiscal_label']}", "",
             f"> {DISCLAIMER}", "", f"## {L['changed']}", ""]
    for f in core[:3]:
        text, _ = fmt.fill(f.template, f.values, f.formats)
        lines.append(f"- {text}")
    lines += ["", f"## {L['findings']}", ""]
    all_sources = []
    for i, f in enumerate(core, 1):
        text, _ = fmt.fill(f.template, f.values, f.formats)
        lines += [f"### {i}. {TITLES.get(f.kind, f.kind)}", "",
                  text, "",
                  f"- **{L['source']}:** " + "; ".join(_cite(s) for s in f.sources),
                  f"- **{L['conf']}:** {f.confidence}",
                  f"- **{L['not']}:** {f.not_mean}", ""]
        all_sources += [s for s in f.sources if s not in all_sources]
    if context:
        lines += [f"## {L['context']}", ""]
        for f in context:
            text, _ = fmt.fill(f.template, f.values, f.formats)
            lines += [f"- {text} ({f.confidence}; {f.not_mean})"]
            all_sources += [s for s in f.sources if s not in all_sources]
        lines.append("")
    lines += [f"## {L['log']}", ""] + [f"- {_cite(s)}" for s in all_sources]
    lines += ["", f"## {L['gloss']}", ""]
    lines += [f"- **{k}:** {v}" for k, v in GLOSSARY[lang].items()]
    lines += ["", f"> {DISCLAIMER}", ""]
    brief = "\n".join(lines)
    validate_brief(findings, brief)   # raises ValidationError: fail closed
    return brief
