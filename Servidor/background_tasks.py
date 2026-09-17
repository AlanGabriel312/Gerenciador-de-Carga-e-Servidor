import subprocess
import json
from database import registrar_telemetria

def ler_bateria_termux():
    try:
        # timeout=2 garante que o bot nao fique congelado se a API do Android demorar
        resultado = subprocess.run(
            ["termux-battery-status"], 
            capture_output=True, 
            text=True, 
            timeout=2
        )
        if resultado.returncode == 0:
            dados = json.loads(resultado.stdout)
            return {
                "porcentagem": dados.get("percentage", 0),
                "status_plug": dados.get("plugged", "UNPLUGGED"),
                "temperatura": dados.get("temperature", 0.0)
            }
    except Exception as e:
        print(f"Erro/Timeout ao ler bateria: {e}")
    return None

alerta_bateria_enviado = False
alerta_temp_enviado = False

def rotina_verificacao_sistema():
    global alerta_bateria_enviado, alerta_temp_enviado
    from telegram_bot import enviar_mensagem_telegram  # Import local previne travamento circular
    
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