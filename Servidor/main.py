from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Servidor rodando no celular!", "dispositivo": "ESP8266 Gerenciador"}