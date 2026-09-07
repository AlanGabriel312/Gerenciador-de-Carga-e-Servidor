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
    texto = "📁 *Seus Arquivos no Servidor:*\n\n"
    vazio = True
    for pasta in ["fotos", "documentos", "diversos"]:
        caminho = os.path.join(STORAGE_DIR, pasta)
        texto += f"📂 *{pasta.capitalize()}*\n"
        if os.path.exists(caminho):
            arquivos = os.listdir(caminho)
            if arquivos:
                vazio = False
                for arq in arquivos:
                    texto += f"  ├ {arq}\n"
            else:
                texto += "  └ _(vazia)_\n"
        texto += "\n"
    
    if vazio:
        texto += "Nenhum arquivo encontrado.\n"
    texto += "💡 *Dica:* Para enviar um arquivo, basta anexar uma foto ou documento no chat!"
    return texto

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
                                    enviar_mensagem_telegram(listar_arquivos())
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
        except Exception as e:
            pass 
        time.sleep(2)