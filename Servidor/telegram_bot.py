import os
import urllib.request
import urllib.parse
import json
import time
from dotenv import load_dotenv

# Carrega as variáveis do .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")

# Dicionário temporário para lembrar qual arquivo você enviou enquanto escolhe a pasta
arquivos_pendentes = {}

def enviar_mensagem_telegram(mensagem: str, teclado_inline=None, chat_id=TELEGRAM_CHAT_ID):
    if not TELEGRAM_TOKEN or not chat_id: return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    dados = {"chat_id": chat_id, "text": mensagem, "parse_mode": "Markdown"}
    
    if teclado_inline:
        dados["reply_markup"] = json.dumps({"inline_keyboard": teclado_inline})
        
    dados_codificados = urllib.parse.urlencode(dados).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=dados_codificados)
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False

def editar_mensagem_telegram(chat_id, message_id, novo_texto):
    """Substitui a mensagem dos botões pelo resultado final (Sucesso/Erro)"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
    dados = {"chat_id": chat_id, "message_id": message_id, "text": novo_texto, "parse_mode": "Markdown"}
    try:
        req = urllib.request.Request(url, data=urllib.parse.urlencode(dados).encode("utf-8"))
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

def baixar_arquivo_telegram(file_id, pasta_destino, nome_sugerido):
    try:
        # 1. Pede ao Telegram o link de download do arquivo interno
        url_info = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
        req = urllib.request.Request(url_info)
        with urllib.request.urlopen(req, timeout=10) as resposta:
            dados = json.loads(resposta.read().decode())
            if not dados.get("ok"): return False
            file_path = dados["result"]["file_path"]
        
        # 2. Faz o download do arquivo diretamente para a pasta do celular
        url_download = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        caminho_final = os.path.join(STORAGE_DIR, pasta_destino, nome_sugerido)
        os.makedirs(os.path.dirname(caminho_final), exist_ok=True)
        
        urllib.request.urlretrieve(url_download, caminho_final)
        return True
    except Exception as e:
        print(f"Erro ao baixar: {e}")
        return False

def listar_arquivos():
    texto = "📁 *Seus Arquivos no Servidor:*\n(Clique no botão para baixar o arquivo de qualquer lugar)"
    
    # Vamos montar um teclado inline com botões para cada arquivo
    teclado = []
    
    for pasta in ["fotos", "documentos", "diversos"]:
        caminho = os.path.join(STORAGE_DIR, pasta)
        if os.path.exists(caminho):
            arquivos = os.listdir(caminho)
            for arq in arquivos:
                # Cada botão carrega o caminho relativo do arquivo
                caminho_relativo = f"{pasta}/{arq}"
                # O Telegram limita o callback_data a 64 bytes, usamos o prefixo dl:
                teclado.append([{"text": f"📥 [{pasta}] {arq}", "callback_data": f"dl:{caminho_relativo}"}])
    
    if not teclado:
        texto = "📁 *Nenhum arquivo encontrado no servidor.*"
        return texto, None
        
    return texto, teclado

def escutar_comandos_telegram():
    from background_tasks import ler_bateria_termux 
    global arquivos_pendentes
    offset = None
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?timeout=20"
            if offset: url += f"&offset={offset}"
            req = urllib.request.Request(url)
            
            with urllib.request.urlopen(req, timeout=25) as resposta:
                dados = json.loads(resposta.read().decode())
                if dados.get("ok"):
                    for update in dados.get("result", []):
                        offset = update["update_id"] + 1
                        
                        # ==========================================
                        # 1. PROCESSA MENSAGENS COMUNS NO CHAT
                        # ==========================================
                        if "message" in update:
                            msg = update["message"]
                            chat_id = str(msg["chat"]["id"])
                            
                            if chat_id != TELEGRAM_CHAT_ID: continue
                            
                            # Se o usuário mandou um Arquivo/PDF/Zip
                            if "document" in msg:
                                file_id = msg["document"]["file_id"]
                                nome = msg["document"].get("file_name", f"doc_{int(time.time())}")
                                arquivos_pendentes[chat_id] = {"file_id": file_id, "nome": nome}
                                
                                teclado = [
                                    [{"text": "📁 Fotos", "callback_data": "pasta:fotos"}, {"text": "📄 Documentos", "callback_data": "pasta:documentos"}],
                                    [{"text": "📦 Diversos", "callback_data": "pasta:diversos"}, {"text": "❌ Cancelar", "callback_data": "pasta:cancelar"}]
                                ]
                                enviar_mensagem_telegram(f"📥 Recebi o documento `{nome}`.\nEm qual pasta devo salvar?", teclado, chat_id)
                            
                            # Se o usuário mandou uma Foto comprimida
                            elif "photo" in msg:
                                file_id = msg["photo"][-1]["file_id"] # Pega a de melhor resolução
                                nome = f"foto_{int(time.time())}.jpg"
                                arquivos_pendentes[chat_id] = {"file_id": file_id, "nome": nome}
                                
                                teclado = [
                                    [{"text": "📁 Fotos", "callback_data": "pasta:fotos"}, {"text": "📄 Documentos", "callback_data": "pasta:documentos"}],
                                    [{"text": "📦 Diversos", "callback_data": "pasta:diversos"}, {"text": "❌ Cancelar", "callback_data": "pasta:cancelar"}]
                                ]
                                enviar_mensagem_telegram(f"🖼️ Recebi uma foto.\nEm qual pasta devo salvar?", teclado, chat_id)
                            
                            # Se o usuário mandou Texto/Comando
                            elif "text" in msg:
                                texto = msg["text"].lower().strip()
                                if texto == "/status":
                                    bateria = ler_bateria_termux()
                                    if bateria:
                                        enviar_mensagem_telegram(f"📊 *Status Atual*\n🔋 Bat: {bateria['porcentagem']}%\n🔌 Conexão: {bateria['status_plug']}\n🌡️ Temp: {bateria['temperatura']}°C")
                                elif texto == "/arquivos":
                                    txt, teclado_arq = listar_arquivos()
                                    enviar_mensagem_telegram(txt, teclado_arq, chat_id)
                                elif texto == "/start" or texto == "oi":
                                    enviar_mensagem_telegram("🤖 *Servidor Ouvindo!*\nComandos:\n`/status` - Bateria\n`/arquivos` - Listar arquivos\n\n_Dica: Para guardar algo no servidor, é só anexar aqui no chat!_")

                        # ==========================================
                        # 2. PROCESSA CLIQUES NOS BOTÕES
                        # ==========================================
                        elif "callback_query" in update:
                            cb = update["callback_query"]
                            chat_id = str(cb["message"]["chat"]["id"])
                            data = cb["data"]
                            msg_id = cb["message"]["message_id"]
                            
                            # Responde pro Telegram apagar o "reloginho" do botão
                            urllib.request.urlopen(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery?callback_query_id={cb['id']}")
                            
                            # Trata a seleção de pastas para upload
                            if data.startswith("pasta:"):
                                pasta = data.split(":")[1]
                                
                                if pasta == "cancelar":
                                    arquivos_pendentes.pop(chat_id, None)
                                    editar_mensagem_telegram(chat_id, msg_id, "❌ *Upload cancelado pelo usuário.*")
                                else:
                                    if chat_id in arquivos_pendentes:
                                        pendente = arquivos_pendentes.pop(chat_id)
                                        editar_mensagem_telegram(chat_id, msg_id, f"⏳ *Baixando do Telegram e salvando em `/{pasta}`...*")
                                        
                                        sucesso = baixar_arquivo_telegram(pendente["file_id"], pasta, pendente["nome"])
                                        
                                        if sucesso:
                                            editar_mensagem_telegram(chat_id, msg_id, f"✅ *Sucesso!* \nArquivo `{pendente['nome']}` salvo na pasta `/{pasta}`.")
                                        else:
                                            editar_mensagem_telegram(chat_id, msg_id, "❌ *Erro ao baixar o arquivo. Ele pode ser muito grande.*")
                                    else:
                                        editar_mensagem_telegram(chat_id, msg_id, "⚠️ O arquivo expirou da memória, tente reenviar.")
                            
                            # Trata o pedido de download de arquivo de qualquer lugar (dl:)
                            elif data.startswith("dl:"):
                                caminho_relativo = data.replace("dl:", "")
                                caminho_absoluto = os.path.join(STORAGE_DIR, caminho_relativo)
                                
                                if os.path.exists(caminho_absoluto):
                                    editar_mensagem_telegram(chat_id, msg_id, f"📤 *Enviando arquivo `{os.path.basename(caminho_absoluto)}`...*")
                                    
                                    url_envio = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
                                    try:
                                        with open(caminho_absoluto, "rb") as f:
                                            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
                                            body = (
                                                f"--{boundary}\r\n"
                                                f"Content-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n"
                                                f"--{boundary}\r\n"
                                                f"Content-Disposition: form-data; name=\"document\"; filename=\"{os.path.basename(caminho_absoluto)}\"\r\n"
                                                f"Content-Type: application/octet-stream\r\n\r\n"
                                            ).encode("utf-8") + f.read() + f"\r\n--{boundary}--\r\n".encode("utf-8")
                                            
                                            req = urllib.request.Request(url_envio, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
                                            urllib.request.urlopen(req, timeout=30)
                                            
                                        editar_mensagem_telegram(chat_id, msg_id, f"✅ *Arquivo `{os.path.basename(caminho_absoluto)}` enviado com sucesso!*")
                                    except Exception as ex:
                                        editar_mensagem_telegram(chat_id, msg_id, f"❌ Erro ao enviar arquivo: {ex}")
                                else:
                                    editar_mensagem_telegram(chat_id, msg_id, "❌ Arquivo não encontrado no servidor.")
        except Exception as e:
            pass 
        time.sleep(2)