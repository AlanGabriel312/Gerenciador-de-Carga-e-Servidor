import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "servidor.db")

def conectar():
    return sqlite3.connect(DB_PATH)

def inicializar_banco():
    conn = conectar()
    cursor = conn.cursor()
    
    # Tabela de Telemetria da Bateria (salva a cada 10 min para não lotar o disco)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetria_bateria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            porcentagem INTEGER,
            status_rele INTEGER,
            temperatura REAL,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de Logs de Execução de Scripts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs_scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_script TEXT,
            status TEXT,
            mensagem_erro TEXT,
            tempo_execucao_ms INTEGER,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def registrar_telemetria(porcentagem, status_rele, temperatura):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO telemetria_bateria (porcentagem, status_rele, temperatura) VALUES (?, ?, ?)",
        (porcentagem, status_rele, temperatura)
    )
    conn.commit()
    conn.close()

def registrar_log_script(nome, status, erro=None, tempo_ms=0):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs_scripts (nome_script, status, mensagem_erro, tempo_execucao_ms) VALUES (?, ?, ?, ?)",
        (nome, status, erro, tempo_ms)
    )
    conn.commit()
    conn.close()