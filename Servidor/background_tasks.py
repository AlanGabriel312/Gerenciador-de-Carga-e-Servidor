import subprocess
import json
from database import registrar_telemetria
from telegram_bot import enviar_mensagem_telegram

def ler_bateria_termux():
    try:
        resultado = subprocess.run(["termux-battery-status"], capture_output=True, text=True)
        dados = json.loads(resultado.stdout)
        return {
            "porcentagem": dados.get("percentage"),
            "status_plug": dados.get("plugged"),
            "temperatura": dados.get("temperature")
        }
    except Exception as e:
        print(f"Erro ao ler bateria: {e}")
        return None

alerta_bateria_enviado = False
alerta_temp_enviado = False

def rotina_verificacao_sistema():
    global alerta_bateria_enviado, alerta_temp_enviado
    
    bateria = ler_bateria_termux()
    if not bateria:
        return

    perc = bateria["porcentagem"]
    temp = bateria["temperatura"]
    
    if perc <= 10 and not alerta_bateria_enviado:
        enviar_mensagem_telegram(f"🚨 ALERTA CRÍTICO: Bateria do servidor em {perc}%! O carregador pode ter falhado.")
        alerta_bateria_enviado = True
    elif perc > 15:
        alerta_bateria_enviado = False

    if temp >= 42.0 and not alerta_temp_enviado:
        enviar_mensagem_telegram(f"🔥 ALERTA DE SUPERAQUECIMENTO: Bateria atingiu {temp}°C!")
        alerta_temp_enviado = True
    elif temp < 39.0:
        alerta_temp_enviado = False

    status_rele_atual = 0 if bateria["status_plug"] == "UNPLUGGED" else 1
    registrar_telemetria(perc, status_rele_atual, temp)