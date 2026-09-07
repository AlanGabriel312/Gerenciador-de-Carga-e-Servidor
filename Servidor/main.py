import os
import threading
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from apscheduler.schedulers.background import BackgroundScheduler

from database import inicializar_banco
from background_tasks import rotina_verificacao_sistema, ler_bateria_termux
from telegram_bot import iniciar_bot_background

app = FastAPI(title="Servidor Central - Android IoT")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")

# Inicializa o Banco SQLite ao subir o servidor
inicializar_banco()

# Configura o Agendador de Tarefas em Segundo Plano (Roda a cada 5 minutos)
scheduler = BackgroundScheduler()
scheduler.add_job(rotina_verificacao_sistema, 'interval', minutes=5)
scheduler.start()

# Inicia o Bot do Telegram em uma Thread separada para não travar o FastAPI
threading.Thread(target=iniciar_bot_background, daemon=True).start()

# ==========================================
# ROTAS DO SERVIDOR DE ARQUIVOS E WEB
# ==========================================
@app.get("/", response_class=HTMLResponse)
def home():
    bateria = ler_bateria_termux()
    porcentagem = bateria.get("porcentagem", "N/A") if bateria else "N/A"
    status_plug = bateria.get("status_plug", "N/A") if bateria else "N/A"

    pastas_html = ""
    for item in os.listdir(STORAGE_DIR):
        caminho_item = os.path.join(STORAGE_DIR, item)
        if os.path.isdir(caminho_item):
            pastas_html += f'<li>📂 <a href="/navegar/{item}"><b>{item}</b></a></li>'

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Servidor Central - Celular</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f9; }}
            .card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            ul {{ list-style-type: none; padding: 0; }}
            li {{ margin: 10px 0; padding: 12px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            a {{ text-decoration: none; color: #007bff; font-size: 18px; }}
        </style>
    </head>
    <body>
        <h1>📱 Servidor Central no Celular</h1>
        <div class="card">
            <h2>🔋 Status da Bateria</h2>
            <p><b>Nível:</b> {porcentagem}%</p>
            <p><b>Conexão:</b> {status_plug}</p>
        </div>
        <div class="card">
            <h2>📁 Servidor de Arquivos</h2>
            <ul>{pastas_html}</ul>
        </div>
    </body>
    </html>
    """

@app.get("/api/comando-esp")
def comando_para_esp8266():
    """Rota consultada pelo ESP8266 a cada 10 segundos"""
    bateria = ler_bateria_termux()
    if not bateria:
        return {"rele": None, "erro": "Falha na leitura"}

    porcentagem = bateria["porcentagem"]
    if porcentagem <= 20:
        return {"rele": 1, "acao": "ligar", "bateria": porcentagem}
    elif porcentagem >= 80:
        return {"rele": 0, "acao": "desligar", "bateria": porcentagem}
    else:
        return {"rele": None, "acao": "manter", "bateria": porcentagem}