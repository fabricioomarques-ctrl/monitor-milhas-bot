from flask import Flask, jsonify

from engine.metrics import carregar_metrics

app = Flask(__name__)


@app.get("/")
def index():
    metrics = carregar_metrics()

    html = f"""
    <html>
      <head>
        <title>Radar de Milhas PRO MAX v4</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 30px; background: #f8f9fb; color: #222; }}
          h1 {{ margin-bottom: 10px; }}
          .card {{ background: white; padding: 16px; border-radius: 10px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
          .muted {{ color: #666; }}
          ul {{ margin-top: 8px; }}
          code {{ background: #eef; padding: 2px 6px; border-radius: 4px; }}
        </style>
      </head>
      <body>
        <h1>Radar de Milhas PRO MAX v4</h1>
        <p class="muted">Painel interno de monitoramento</p>

        <div class="card">
          <h2>Status</h2>
          <p><b>Última execução:</b> {metrics.get("last_run", "")}</p>
          <p><b>Fontes monitoradas:</b> {metrics.get("sources_monitored", 0)}</p>
          <p><b>Fontes ativas:</b> {metrics.get("sources_active", 0)}</p>
          <p><b>Fontes com erro:</b> {metrics.get("sources_error", 0)}</p>
          <p><b>Itens coletados:</b> {metrics.get("items_collected", 0)}</p>
          <p><b>Itens descartados:</b> {metrics.get("items_discarded", 0)}</p>
          <p><b>Oportunidades detectadas:</b> {metrics.get("items_detected", 0)}</p>
          <p><b>Alertas enviados:</b> {metrics.get("items_sent", 0)}</p>
          <p><b>Último erro:</b> {metrics.get("last_error", "nenhum") or "nenhum"}</p>
        </div>

        <div class="card">
          <h2>Detectores ativos</h2>
          <ul>
            {''.join(f"<li>{item}</li>" for item in metrics.get("detectors_active", []))}
          </ul>
        </div>

        <div class="card">
          <h2>Descartes por filtro</h2>
          <ul>
            {''.join(f"<li>{k}: {v}</li>" for k, v in metrics.get("discard_reasons", {}).items()) or "<li>nenhum</li>"}
          </ul>
        </div>

        <div class="card">
          <h2>Fontes</h2>
          <ul>
            {''.join(f"<li>{f.get('tipo')} / {f.get('fonte')} — {f.get('status')} {('- ' + f.get('erro')) if f.get('erro') else ''}</li>" for f in metrics.get("sources", [])) or "<li>nenhuma</li>"}
          </ul>
        </div>

        <div class="card">
          <h2>Últimos resultados</h2>
          <ul>
            {''.join(f"<li>{r.get('titulo')} — score {r.get('score', 0)}/10</li>" for r in metrics.get("last_results", [])) or "<li>nenhum</li>"}
          </ul>
        </div>
      </body>
    </html>
    """
    return html


@app.get("/api/metrics")
def api_metrics():
    return jsonify(carregar_metrics())
