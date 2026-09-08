import os
import sys
import time
import subprocess
from database import registrar_execucao_script

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts_iot")

def listar_scripts_disponiveis():
    if not os.path.exists(SCRIPTS_DIR):
        os.makedirs(SCRIPTS_DIR, exist_ok=True)
        return []
    
    return sorted([f[:-3] for f in os.listdir(SCRIPTS_DIR) if f.endswith(".py") and not f.startswith("__")])

def rodar_script_por_nome(nome_script):
    """Executa o script isoladamente em um subprocesso e registra a telemetria"""
    caminho_script = os.path.join(SCRIPTS_DIR, f"{nome_script}.py")
    
    if not os.path.exists(caminho_script):
        return False, "Script não encontrado."
    
    inicio = time.time()
    try:
        # Usa sys.executable para garantir o mesmo Python e envia a execução
        processo = subprocess.run(
            [sys.executable, caminho_script],
            capture_output=True,
            text=True,
            timeout=15
        )
        tempo_ms = int((time.time() - inicio) * 1000)
        
        if processo.returncode == 0:
            saida = processo.stdout.strip() or "Executado com sucesso (sem output)."
            registrar_execucao_script(nome_script, "SUCESSO", "", tempo_ms)
            return True, f"Sucesso em {tempo_ms}ms:\n`{saida[:150]}`"
        else:
            erro_msg = processo.stderr.strip() or "Erro desconhecido durante a execução."
            registrar_execucao_script(nome_script, "ERRO", erro_msg[:200], tempo_ms)
            return False, f"Erro em {tempo_ms}ms:\n`{erro_msg[:150]}`"
            
    except subprocess.TimeoutExpired:
        tempo_ms = int((time.time() - inicio) * 1000)
        registrar_execucao_script(nome_script, "TIMEOUT", "Excedeu o tempo limite de 15s", tempo_ms)
        return False, f"Tempo limite excedido (mais de 15s)."
    except Exception as e:
        tempo_ms = int((time.time() - inicio) * 1000)
        registrar_execucao_script(nome_script, "ERRO_EXCECAO", str(e), tempo_ms)
        return False, f"Falha de execução: {str(e)}"