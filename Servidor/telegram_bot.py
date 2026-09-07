import os
import urllib.request
import urllib.parse
import json
from background_tasks import ler_bateria_termux

TELEGRAM_TOKEN = "8979638708:AAGccCu9K8jC1bLJ6NkvSs-uvHZJS_4BfOA"
TELEGRAM_CHAT_ID = "1181317619"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")

def enviar_mensagem_telegram(mensagem: str):
    """Envia uma mensagem de texto usando diretamente a API HTTP do Telegram."""
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

def verificar_comandos_telegram():
    """
    Função simples que pode rodar em segundo plano para checar mensagens 
    ou enviar relatórios automáticos.
    """
    bateria = ler_bateria_termux()
    if bateria:
        texto = (
            f"🤖 *Relatório Periódico do Servidor*\n"
            f"🔋 Bateria: {bateria['porcentagem']}%\n"
            f"🔌 Conexão: {bateria['status_plug']}\n"
            f"🌡️ Temperatura: {bateria['temperatura']}°C"
        )
        enviar_mensagem_telegram(texto)