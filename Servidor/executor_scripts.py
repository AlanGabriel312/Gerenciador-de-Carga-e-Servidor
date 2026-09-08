import os
import time
import subprocess
from database import registrar_execucao_script

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts_iot")

def listar_scripts_disponiveis():
    if not os.path.exists(SCRIPTS_DIR):
        os.makedirs(SCRIPTS_DIR, exist_ok=True)
        return []
    
    # Retorna todos os arquivos .py na pasta scripts_iot (ignora arquivos ocultos ou __init__)
    return sorted([f[:-3] for f in os.listdir(SCRIPTS_DIR) if f.endswith(".py") and not f.startswith("__")])

def rodar_script_por_nome(nome_script):
    """Executa o script isoladamente em um subprocesso e registra a telemetria"""
    caminho_script = os.path.join(SCRIPTS_DIR, f"{nome_script}.py")
    
    if not os.path.exists(caminho_script):
        return False, "Script não encontrado."
    
    inicio = time.time()
    try:
        resultado = subprocess.run(["python", caminho_script], capture_output=True, text=True, timeout=60)
        tempo_ms = int((time.time() - inicio) * 1000)
        
        if resultado.returncode == 0:
            registrar_execucao_script(nome_script, "SUCESSO", "", tempo_ms)
            msg_saida = resultado.stdout.strip() or "Executado sem saída de texto."
            return True, f"Sucesso em {tempo_ms}ms:\n`{msg_saida[:150]}`"
        else:
            erro_msg = resultado.stderr.strip() or "Erro desconhecido na execução."
            registrar_execucao_script(nome_script, "ERRO", erro_msg[:200], tempo_ms)
            return False, f"Erro ({tempo_ms}ms):\n`{erro_msg[:150]}`"
            
    except Exception as e:
        tempo_ms = int((time.time() - inicio) * 1000)
        registrar_execucao_script(nome_script, "ERRO_EXCECAO", str(e), tempo_ms)
        return False, f"Falha de execução: {str(e)}"