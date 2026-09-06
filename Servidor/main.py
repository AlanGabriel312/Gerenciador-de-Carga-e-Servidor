import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Servidor de Arquivos do Celular")

# Diretório base onde os arquivos ficam salvos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")

# Cria as pastas padrão caso não existam
PASTAS_PADRAO = ["fotos", "documentos", "diversos"]
for pasta in PASTAS_PADRAO:
    os.makedirs(os.path.join(STORAGE_DIR, pasta), exist_ok=True)


@app.get("/", response_class=HTMLResponse)
def listar_pastas():
    """Página inicial com a lista das pastas principais"""
    pastas_html = ""
    for item in os.listdir(STORAGE_DIR):
        caminho_item = os.path.join(STORAGE_DIR, item)
        if os.path.isdir(caminho_item):
            pastas_html += f'<li>📂 <a href="/navegar/{item}"><b>{item}</b></a></li>'

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Servidor de Arquivos</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f9; }}
            h1 {{ color: #333; }}
            ul {{ list-style-type: none; padding: 0; }}
            li {{ margin: 10px 0; padding: 12px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            a {{ text-decoration: none; color: #007bff; font-size: 18px; }}
        </style>
    </head>
    <body>
        <h1>📁 Servidor de Arquivos Local</h1>
        <hr>
        <h3>Categorias Principais:</h3>
        <ul>{pastas_html}</ul>
    </body>
    </html>
    """
    return html_content


@app.get("/navegar/{caminho_subpasta:path}", response_class=HTMLResponse)
def navegar_pasta(caminho_subpasta: str):
    """Navega por subpastas e lista arquivos com opção de upload"""
    caminho_completo = os.path.join(STORAGE_DIR, caminho_subpasta)

    if not os.path.exists(caminho_completo):
        raise HTTPException(status_code=404, detail="Pasta não encontrada")

    # Lista subpastas e arquivos
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

    html_content = f"""
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
        <a href="/">⬅️ Voltar ao Início</a> | <a href="javascript:history.back()">🔙 Voltar</a>
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
    return html_content


@app.post("/upload/{caminho_subpasta:path}")
async def receber_arquivo(caminho_subpasta: str, file: UploadFile = File(...)):
    """Recebe arquivos do computador/celular e salva no diretório correto"""
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
    """Faz o download ou exibição do arquivo escolhido"""
    caminho_completo = os.path.join(STORAGE_DIR, caminho_arquivo)
    if os.path.exists(caminho_completo) and os.path.isfile(caminho_completo):
        return FileResponse(caminho_completo)
    raise HTTPException(status_code=404, detail="Arquivo não encontrado")