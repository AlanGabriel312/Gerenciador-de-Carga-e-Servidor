import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from background_tasks import ler_bateria_termux

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Servidor Central Online!*\n\n"
        "Comandos disponíveis:\n"
        "/status - Vê a bateria e temperatura atuais\n\n"
        "📁 *Dica:* Você pode enviar qualquer foto, vídeo ou documento direto no chat e eu salvo no servidor!",
        parse_mode="Markdown"
    )

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bateria = ler_bateria_termux()
    if not bateria:
        await update.message.reply_text("❌ Erro ao ler sensores do celular.")
        return
    
    texto = (
        f"📊 *Status do Servidor*\n"
        f"🔋 Bateria: {bateria['porcentagem']}%\n"
        f"🔌 Conexão: {bateria['status_plug']}\n"
        f"🌡️ Temperatura: {bateria['temperatura']}°C"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")

async def receber_arquivos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        file = await update.message.document.get_file()
        filename = update.message.document.file_name
        pasta_destino = os.path.join(STORAGE_DIR, "documentos")
    elif update.message.photo:
        file = await update.message.photo[-1].get_file()
        filename = f"foto_{file.file_unique_id}.jpg"
        pasta_destino = os.path.join(STORAGE_DIR, "fotos")
    else:
        return

    os.makedirs(pasta_destino, exist_ok=True)
    caminho_final = os.path.join(pasta_destino, filename)
    
    await file.download_to_drive(caminho_final)
    await update.message.reply_text(f"✅ Arquivo salvo com sucesso em `/{os.path.basename(pasta_destino)}/{filename}`", parse_mode="Markdown")

def iniciar_bot_background():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, receber_arquivos))
    app.run_polling(drop_pending_updates=True)