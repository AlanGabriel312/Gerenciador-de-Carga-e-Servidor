import os
import urllib.request
import urllib.parse
import json
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env (na mesma pasta ou na raiz)
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_mensagem_telegram(mensagem: str):
    """Envia uma mensagem de texto usando diretamente a API HTTP do Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Erro: Credenciais do Telegram não encontradas no .env")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    dados = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown"
    }
    dados_codificados = urllib.parse.urlencode(dados).encode("utf-8")
    
    try:
        requisicao = urllib.request.Request(url, data=dados_codificados)
        with urllib.request.urlopen(requisicao, timeout=5) as resposta:
            resultado = json.loads(resposta.read().decode())
            return resultado.get("ok", False)
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem para o Telegram: {e}")
        return False