import os
import urllib.request
import urllib.parse
import json
import time
from dotenv import load_dotenv

from executor_scripts import listar_scripts_disponiveis, rodar_script_por_nome
from database import obter_estatisticas_script

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")

arquivos_pendentes = {}
navegacao_cache = {}
ITENS_POR_PAGINA = 5

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

def editar_mensagem_telegram(chat_id, message_id, novo_texto, teclado_inline=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
    dados = {"chat_id": chat_id, "message_id": message_id, "text": novo_texto, "parse_mode": "Markdown"}
    if teclado_inline:
        dados["reply_markup"] = json.dumps({"inline_keyboard": teclado_inline})
    try:
        req = urllib.request.Request(url, data=urllib.parse.urlencode(dados).encode("utf-8"))
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

def baixar_arquivo_telegram(file_id, pasta_destino, nome_sugerido):
    try:
        url_info = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
        req = urllib.request.Request(url_info)
        with urllib.request.urlopen(req, timeout=10) as resposta:
            dados = json.loads(resposta.read().decode())
            if not dados.get("ok"): return False
            file_path = dados["result"]["file_path"]
        
        url_download = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        caminho_final = os.path.join(STORAGE_DIR, pasta_destino, nome_sugerido)
        os.makedirs(os.path.dirname(caminho_final), exist_ok=True)
        urllib.request.urlretrieve(url_download, caminho_final)
        return True
    except Exception as e:
        print(f"Erro ao baixar: {e}")
        return False

def registrar_cache_rota(caminho_relativo, pagina):
    chave = f"{caminho_relativo}:::{pagina}"
    for k, v in navegacao_cache.items():
        if v == chave:
            return k
    novo_id = str(int(time.time() * 1000))[-6:]
    navegacao_cache[novo_id] = chave
    return novo_id

def gerar_teclado_diretorio(caminho_relativo="", pagina=0):
    caminho_relativo = caminho_relativo.strip("/")
    caminho_absoluto = os.path.join(STORAGE_DIR, caminho_relativo) if caminho_relativo else STORAGE_DIR

    if not os.path.exists(caminho_absoluto):
        return f"❌ Diretório não encontrado: `/{caminho_relativo}`", None

    try:
        itens = sorted(os.listdir(caminho_absoluto))
    except Exception:
        return "❌ Erro ao ler o diretório.", None

    pastas = []
    arquivos = []

    for item in itens:
        full_path = os.path.join(caminho_absoluto, item)
        if os.path.isdir(full_path):
            pastas.append(item)
        else:
            arquivos.append(item)

    todos_elementos = [{"tipo": "pasta", "nome": p} for p in pastas] + [{"tipo": "arquivo", "nome": a} for a in arquivos]
    
    total_itens = len(todos_elementos)
    inicio = pagina * ITENS_POR_PAGINA
    fim = inicio + ITENS_POR_PAGINA
    itens_pagina = todos_elementos[inicio:fim]

    teclado = []
    for el in itens_pagina:
        sub_caminho = f"{caminho_relativo}/{el['nome']}" if caminho_relativo else el['nome']
        if el["tipo"] == "pasta":
            cache_id = registrar_cache_rota(sub_caminho, 0)
            teclado.append([{"text": f"📂 {el['nome']}", "callback_data": f"dir:{cache_id}"}])
        else:
            teclado.append([{"text": f"📥 {el['nome']}", "callback_data": f"dl:{sub_caminho}"}])

    botoes_paginacao = []
    if pagina > 0:
        cache_ant = registrar_cache_rota(caminho_relativo, pagina - 1)
        botoes_paginacao.append({"text": "⬅️ Anterior", "callback_data": f"dir:{cache_ant}"})
    if fim < total_itens:
        cache_prox = registrar_cache_rota(caminho_relativo, pagina + 1)
        botoes_paginacao.append({"text": "Próxima ➡️", "callback_data": f"dir:{cache_prox}"})
    
    if botoes_paginacao:
        teclado.append(botoes_paginacao)

    if caminho_relativo:
        pai = os.path.dirname(caminho_relativo)
        cache_pai = registrar_cache_rota(pai, 0)
        teclado.append([{"text": "🔙 Voltar", "callback_data": f"dir:{cache_pai}"}])
    else:
        teclado.append([{"text": "❌ Fechar Menu", "callback_data": "dir:fechar"}])

    exibir_caminho = f"/{caminho_relativo}" if caminho_relativo else "/raiz"
    texto = f"📁 *Explorador:* `{exibir_caminho}`\n(Página {pagina + 1} de {max(1, (total_itens + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)})"
    return texto, teclado

def escutar_comandos_telegram():
    from background_tasks import ler_bateria_termux 
    global arquivos_pendentes, navegacao_cache
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
                        
                        if "message" in update:
                            msg = update["message"]
                            chat_id = str(msg["chat"]["id"])
                            if chat_id != TELEGRAM_CHAT_ID: continue
                            
                            if "document" in msg:
                                file_id = msg["document"]["file_id"]
                                nome = msg["document"].get("file_name", f"doc_{int(time.time())}")
                                arquivos_pendentes[chat_id] = {"file_id": file_id, "nome": nome}
                                teclado = [
                                    [{"text": "📁 Fotos", "callback_data": "pasta:fotos"}, {"text": "📄 Docs", "callback_data": "pasta:docs"}],
                                    [{"text": "📦 Diversos", "callback_data": "pasta:diversos"}, {"text": "❌ Cancelar", "callback_data": "pasta:cancelar"}]
                                ]
                                enviar_mensagem_telegram(f"📥 Recebi o documento `{nome}`.\nEm qual pasta principal devo salvar?", teclado, chat_id)
                            
                            elif "photo" in msg:
                                file_id = msg["photo"][-1]["file_id"]
                                nome = f"foto_{int(time.time())}.jpg"
                                arquivos_pendentes[chat_id] = {"file_id": file_id, "nome": nome}
                                teclado = [
                                    [{"text": "📁 Fotos", "callback_data": "pasta:fotos"}, {"text": "📄 Docs", "callback_data": "pasta:docs"}],
                                    [{"text": "📦 Diversos", "callback_data": "pasta:diversos"}, {"text": "❌ Cancelar", "callback_data": "pasta:cancelar"}]
                                ]
                                enviar_mensagem_telegram(f"🖼️ Recebi uma foto.\nEm qual pasta principal devo salvar?", teclado, chat_id)
                            
                            elif "text" in msg:
                                texto = msg["text"].lower().strip()
                                if texto == "/status":
                                    bateria = ler_bateria_termux()
                                    if bateria:
                                        enviar_mensagem_telegram(f"📊 *Status Atual*\n🔋 Bat: {bateria['porcentagem']}%\n🔌 Conexão: {bateria['status_plug']}\n🌡️ Temp: {bateria['temperatura']}°C", chat_id=chat_id)
                                elif texto == "/arquivos":
                                    txt, teclado_arq = gerar_teclado_diretorio("", 0)
                                    enviar_mensagem_telegram(txt, teclado_arq, chat_id=chat_id)
                                elif texto == "/scripts":
                                    scripts = listar_scripts_disponiveis()
                                    if not scripts:
                                        enviar_mensagem_telegram("📦 *Nenhum script encontrado na pasta `scripts_iot`.*", chat_id=chat_id)
                                    else:
                                        teclado = [[{"text": f"⚙️ {s}", "callback_data": f"script_info:{s}"}] for s in scripts]
                                        teclado.append([{"text": "❌ Fechar Menu", "callback_data": "dir:fechar"}])
                                        enviar_mensagem_telegram("⚙️ *Gerenciador de Scripts IoT*\nSelecione um script abaixo para ver detalhes:", teclado_inline=teclado, chat_id=chat_id)
                                elif texto in ["/start", "oi", "olá"]:
                                    enviar_mensagem_telegram("🤖 *Servidor Ouvindo!*\nComandos:\n`/status` - Bateria\n`/arquivos` - Navegar pelas pastas\n`/scripts` - Automações IoT\n\n_Dica: Para guardar algo, é só anexar aqui no chat!_", chat_id=chat_id)

                        elif "callback_query" in update:
                            cb = update["callback_query"]
                            chat_id = str(cb["message"]["chat"]["id"])
                            if chat_id != TELEGRAM_CHAT_ID: continue
                            
                            data = cb["data"]
                            msg_id = cb["message"]["message_id"]
                            
                            urllib.request.urlopen(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery?callback_query_id={cb['id']}")
                            
                            if data.startswith("pasta:"):
                                pasta = data.split(":")[1]
                                if pasta == "cancelar":
                                    arquivos_pendentes.pop(chat_id, None)
                                    editar_mensagem_telegram(chat_id, msg_id, "❌ *Upload cancelado.*")
                                else:
                                    if chat_id in arquivos_pendentes:
                                        pendente = arquivos_pendentes.pop(chat_id)
                                        editar_mensagem_telegram(chat_id, msg_id, f"⏳ *Salvando em `/{pasta}`...*")
                                        sucesso = baixar_arquivo_telegram(pendente["file_id"], pasta, pendente["nome"])
                                        if sucesso:
                                            editar_mensagem_telegram(chat_id, msg_id, f"✅ *Sucesso!* Arquivo salvo em `/{pasta}`.")
                                        else:
                                            editar_mensagem_telegram(chat_id, msg_id, "❌ Erro ao baixar arquivo.")
                                    else:
                                        editar_mensagem_telegram(chat_id, msg_id, "⚠️ Arquivo expirado, envie novamente.")
                            
                            elif data.startswith("dir:"):
                                cache_id = data.replace("dir:", "")
                                if cache_id == "fechar":
                                    editar_mensagem_telegram(chat_id, msg_id, "📁 *Menu fechado.*")
                                    continue
                                    
                                if cache_id in navegacao_cache:
                                    info_cache = navegacao_cache[cache_id]
                                    sub_dir, pagina_str = info_cache.rsplit(":::", 1)
                                    pagina = int(pagina_str)
                                    txt, teclado_dir = gerar_teclado_diretorio(sub_dir, pagina)
                                    editar_mensagem_telegram(chat_id, msg_id, txt, teclado_dir)
                                else:
                                    editar_mensagem_telegram(chat_id, msg_id, "⚠️ Sessão expirada. Digite `/arquivos` novamente.")
                            
                            elif data.startswith("dl:"):
                                caminho_relativo = data.replace("dl:", "")
                                caminho_absoluto = os.path.join(STORAGE_DIR, caminho_relativo)
                                
                                if os.path.exists(caminho_absoluto):
                                    editar_mensagem_telegram(chat_id, msg_id, f"📤 *Enviando arquivo...*")
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
                                        editar_mensagem_telegram(chat_id, msg_id, f"✅ *Arquivo enviado com sucesso!*")
                                    except Exception as ex:
                                        editar_mensagem_telegram(chat_id, msg_id, f"❌ Erro ao enviar: {ex}")
                                else:
                                    editar_mensagem_telegram(chat_id, msg_id, "❌ Arquivo não encontrado.")

                            # GERENCIAMENTO DE SCRIPTS VIA TELEGRAM
                            elif data.startswith("script_info:"):
                                nome_script = data.replace("script_info:", "")
                                stats = obter_estatisticas_script(nome_script)
                                
                                texto_painel = (
                                    f"⚙️ *Script:* `{nome_script}`\n\n"
                                    f"📊 *Total de Execuções:* {stats['total']}\n"
                                    f"🕒 *Última Execução:* {stats['ultima_data']}\n"
                                    f"⚡ *Último Status:* `{stats['ultimo_status']}`\n"
                                    f"⏱️ *Tempo do Último Run:* {stats['tempo']}"
                                )
                                
                                teclado_acao = [
                                    [{"text": "▶️ Executar Agora", "callback_data": f"script_run:{nome_script}"}],
                                    [{"text": "🔙 Voltar à Lista", "callback_data": "script_voltar"}]
                                ]
                                editar_mensagem_telegram(chat_id, msg_id, texto_painel, teclado_acao)
                                
                            elif data.startswith("script_run:"):
                                nome_script = data.replace("script_run:", "")
                                editar_mensagem_telegram(chat_id, msg_id, f"⏳ *Executando `{nome_script}`...*")
                                
                                sucesso, mensagem = rodar_script_por_nome(nome_script)
                                stats = obter_estatisticas_script(nome_script)
                                icone = "✅" if sucesso else "❌"
                                
                                texto_resultado = (
                                    f"{icone} *Resultado:*\n{mensagem}\n\n"
                                    f"⚙️ *Script:* `{nome_script}`\n"
                                    f"📊 *Total Execuções:* {stats['total']}"
                                )
                                
                                teclado_acao = [
                                    [{"text": "▶️ Executar Novamente", "callback_data": f"script_run:{nome_script}"}],
                                    [{"text": "🔙 Voltar à Lista", "callback_data": "script_voltar"}]
                                ]
                                editar_mensagem_telegram(chat_id, msg_id, texto_resultado, teclado_acao)
                                
                            elif data == "script_voltar":
                                scripts = listar_scripts_disponiveis()
                                teclado = [[{"text": f"⚙️ {s}", "callback_data": f"script_info:{s}"}] for s in scripts]
                                teclado.append([{"text": "❌ Fechar Menu", "callback_data": "dir:fechar"}])
                                editar_mensagem_telegram(chat_id, msg_id, "⚙️ *Gerenciador de Scripts IoT*\nSelecione um script abaixo:", teclado)

        except Exception as e:
            pass 
        time.sleep(2)