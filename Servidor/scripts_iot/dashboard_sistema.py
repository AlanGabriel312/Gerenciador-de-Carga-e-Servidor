import os
import sys
import sqlite3
import shutil
import urllib.request

# Garante acesso à raiz do projeto para ler o servidor.db e funções
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAIZ_SERVIDOR = os.path.join(BASE_DIR, "..")
sys.path.append(RAIZ_SERVIDOR)

DB_PATH = os.path.join(RAIZ_SERVIDOR, "servidor.db")

def obter_dados_dashboard():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Métricas de Execução de Scripts
    try:
        cursor.execute("SELECT COUNT(*) FROM logs_scripts")
        total_scripts = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM logs_scripts WHERE status = 'SUCESSO'")
        scripts_sucesso = cursor.fetchone()[0]
    except Exception:
        total_scripts, scripts_sucesso = 0, 0

    # 2. Registros de Telemetria da Bateria no Banco
    try:
        cursor.execute("SELECT COUNT(*), AVG(porcentagem), AVG(temperatura) FROM telemetria_bateria")
        row_bat = cursor.fetchone()
        total_leituras_bat = row_bat[0] or 0
        media_bat = row_bat[1] or 0.0
        media_temp = row_bat[2] or 0.0
    except Exception:
        total_leituras_bat, media_bat, media_temp = 0, 0.0, 0.0

    conn.close()

    # 3. Armazenamento Interno
    total_d, usado_d, livre_d = shutil.disk_usage(RAIZ_SERVIDOR)
    gb_livre = livre_d / (1024 ** 3)
    pct_livre = (livre_d / total_d) * 100

    # 4. Formatação do Painel / Dashboard em Markdown
    taxa_sucesso = (scripts_sucesso / total_scripts * 100) if total_scripts > 0 else 100.0

    dashboard_texto = (
        f"📊 *DASHBOARD DE DIAGNÓSTICO DO SERVIDOR*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚙️ *SISTEMA & SCRIPTS*\n"
        f"• Total de Robôs Rodados: *{total_scripts}*\n"
        f"• Taxa de Sucesso: *{taxa_sucesso:.1f}%*\n\n"
        f"🔋 *HISTÓRICO DE ENERGIA (BANCO)*\n"
        f"• Checagens Registradas: *{total_leituras_bat}*\n"
        f"• Média de Carga Histórica: *{media_bat:.1f}%*\n"
        f"• Temperatura Média: *{media_temp:.1f}°C*\n\n"
        f"💾 *ARMAZENAMENTO*\n"
        f"• Espaço Livre no Celular: *{gb_livre:.2f} GB* ({pct_livre:.1f}%)\n\n"
        f"Status: 🟢 *Operacional e Estável*"
    )
    
    return dashboard_texto

if __name__ == "__main__":
    # O print é capturado pelo Telegram e exibido na caixa de texto do resultado!
    print(obter_dados_dashboard())