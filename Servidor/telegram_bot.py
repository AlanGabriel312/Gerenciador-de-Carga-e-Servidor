import os
import urllib.request
import urllib.parse
import json
import time
from dotenv import load_dotenv

# Carrega as variáveis do .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_mensagem_telegram(mensagem: str):
    """Envia uma mensagem de texto."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    dados = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    dados_codificados = urllib.parse.urlencode(dados).encode("utf-8")
    
    try:
        req = urllib.request.Request(url, data=dados_codificados)
        with urllib.request.urlopen(req, timeout=5) as resposta:
            return json.loads(resposta.read().decode()).get("ok", False)
    except Exception:
        return False

def escutar_comandos_telegram():
    """Roda em segundo plano lendo as mensagens sem travar o servidor."""
    # Importado dentro da função para evitar erro de referência circular
    from background_tasks import ler_bateria_termux 
    
    offset = None
    while True:
        try:
            # Consulta a API do Telegram esperando por novas mensagens (Long Polling)
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?timeout=20"
            if offset:
                url += f"&offset={offset}"
            
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=25) as resposta:
                dados = json.loads(resposta.read().decode())
                
                if dados.get("ok"):
                    for update in dados.get("result", []):
                        offset = update["update_id"] + 1
                        
                        if "message" in update and "text" in update["message"]:
                            texto = update["message"]["text"].lower().strip()
                            chat_id = str(update["message"]["chat"]["id"])
                            
                            if chat_id == TELEGRAM_CHAT_ID:
                                if texto == "/status":
                                    bateria = ler_bateria_termux()
                                    if bateria:
                                        msg = (f"📊 *Status Atual do Servidor*\n"
                                               f"🔋 Bateria: {bateria['porcentagem']}%\n"
                                               f"🔌 Conexão: {bateria['status_plug']}\n"
                                               f"🌡️ Temp: {bateria['temperatura']}°C")
                                        enviar_mensagem_telegram(msg)
                                elif texto == "/start" or texto == "oi":
                                    enviar_mensagem_telegram("🤖 *Servidor Online e Ouvindo!*\nDigite `/status` para ver a bateria.")
        except Exception:
            pass # Ignora erros de internet ou timeout e tenta de novo
        
        time.sleep(2) # Pausa leve para não sobrecarregar