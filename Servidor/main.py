import os
import subprocess
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

app = FastAPI(title="Servidor de Arquivos e Gerenciador de Carga")

# ==========================================
# CONFIGURAÇÃO DO SERVIDO DE ARQUIVOS
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")

PASTAS_PADRAO = ["fotos", "documentos", "diversos"]
for pasta in PASTAS_PADRAO:
    os.makedirs(os.path.join(STORAGE_DIR, pasta), exist_ok=True)


@app.get("/", response_class=HTMLResponse)
def home():
    """Página principal com o status da bateria e links do servidor de arquivos"""
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
            h1 {{ color: #333; }}
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


@app.get("/navegar/{caminho_subpasta:path}", response_class=HTMLResponse)
def navegar_pasta(caminho_subpasta: str):
    caminho_completo = os.path.join(STORAGE_DIR, caminho_subpasta)

    if not os.path.exists(caminho_completo):
        raise HTTPException(status_code=404, detail="Pasta não encontrada")

    itens = os.listdir(caminho_completo)
    pastas_html = ""
    arquivos_html = ""

    for item in itens:
        caminho_item = os.path.join(caminho_completo, item)
        rel_path = os.path.join(caminho_subpasta, item)
        
        if os.path.isdir(caminho_item):
            pastas_html += f'<li>📂 <a href="/navegar/{rel_path}"><b>{item}/</b></a></li>'
        else:
            arquivos_html += f'<li>📄 <a href="/download/{rel_path}" target="_blank">{item}</a></li>'

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Navegando: {caminho_subpasta}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f9; }}
            ul {{ list-style-type: none; padding: 0; }}
            li {{ margin: 8px 0; padding: 10px; background: white; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            a {{ text-decoration: none; color: #007bff; }}
            .upload-box {{ background: #e9ecef; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            .btn {{ background: #28a745; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; }}
        </style>
    </head>
    <body>
        <a href="/">⬅️ Voltar ao Início</a>
        <h2>📍 Pasta atual: /{caminho_subpasta}</h2>

        <div class="upload-box">
            <h3>📤 Enviar arquivo para esta pasta:</h3>
            <form action="/upload/{caminho_subpasta}" enctype="multipart/form-data" method="post">
                <input name="file" type="file" required>
                <input type="submit" value="Enviar Arquivo" class="btn">
            </form>
        </div>

        <hr>
        <h3>Subpastas:</h3>
        <ul>{pastas_html if pastas_html else "<i>Nenhuma subpasta.</i>"}</ul>

        <h3>Arquivos:</h3>
        <ul>{arquivos_html if arquivos_html else "<i>Nenhum arquivo nesta pasta.</i>"}</ul>
    </body>
    </html>
    """


@app.post("/upload/{caminho_subpasta:path}")
async def receber_arquivo(caminho_subpasta: str, file: UploadFile = File(...)):
    caminho_destino = os.path.join(STORAGE_DIR, caminho_subpasta, file.filename)
    
    with open(caminho_destino, "wb") as buffer:
        buffer.write(await file.read())
        
    return HTMLResponse(content=f"""
        <script>
            alert("Arquivo '{file.filename}' enviado com sucesso!");
            window.location.href = "/navegar/{caminho_subpasta}";
        </script>
    """)


@app.get("/download/{caminho_arquivo:path}")
def baixar_arquivo(caminho_arquivo: str):
    caminho_completo = os.path.join(STORAGE_DIR, caminho_arquivo)
    if os.path.exists(caminho_completo) and os.path.isfile(caminho_completo):
        return FileResponse(caminho_completo)
    raise HTTPException(status_code=404, detail="Arquivo não encontrado")


# ==========================================
# INTEGRAÇÃO COM BATERIA E ESP8266
# ==========================================
def ler_bateria_termux():
    """Executa o comando nativo do Termux para ler a bateria do celular"""
    try:
        resultado = subprocess.run(["termux-battery-status"], capture_output=True, text=True)
        dados = json.loads(resultado.stdout)
        return {
            "porcentagem": dados.get("percentage"),
            "status_plug": dados.get("plugged"),  # UNPLUGGED, PLUGGED_AC, etc.
            "temperatura": dados.get("temperature")
        }
    except Exception as e:
        print(f"Erro ao ler bateria do Termux: {e}")
        return None


@app.get("/api/bateria")
def api_status_bateria():
    """Retorna os dados da bateria em formato JSON"""
    dados = ler_bateria_termux()
    if dados:
        return dados
    raise HTTPException(status_code=500, detail="Não foi possível ler a bateria do dispositivo")


@app.get("/api/comando-esp")
def comando_para_esp8266():
    """
    Rota que o ESP8266 consulta para saber se deve ligar ou desligar o carregador.
    - Bateria <= 20%: manda LIGAR o relé
    - Bateria >= 80%: manda DESLIGAR o relé
    """
    bateria = ler_bateria_termux()
    if not bateria:
        return {"rele": None, "erro": "Falha na leitura da bateria"}

    porcentagem = bateria["porcentagem"]

    if porcentagem <= 20:
        return {"rele": 1, "acao": "ligar", "bateria": porcentagem}
    elif porcentagem >= 80:
        return {"rele": 0, "acao": "desligar", "bateria": porcentagem}
    else:
        return {"rele": None, "acao": "manter", "bateria": porcentagem}