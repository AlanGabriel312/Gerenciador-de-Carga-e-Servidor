# 📱 Servidor Central Android & Central de Automação IoT

Este projeto transforma um smartphone Android antigo em um servidor de automação residencial, gerenciador de arquivos e central IoT 24/7.

O ecossistema é alimentado por **FastAPI**, **SQLite**, **Telebot/Bot do Telegram com IA de Voz** rodando no **Termux**, além de um hardware dedicado (**ESP8266 + Relé**) responsável pela gestão inteligente de carga do próprio celular, alojado em uma case personalizada impressa em PLA.

---

## 🛠️ Arquitetura do Sistema

```text
+----------------------------------+

|    Bot do Telegram (Interface)   |
| - Comandos de Voz (Google Speech)|
| - Gestão de Arquivos & Scripts   |
+----------------+-----------------+
                 |
                 v
+-----------------------+  HTTP  +--------------------+        +------------------------+

|    ESP8266 + Relé     | <----> |  Servidor Termux   | <----> |      Banco SQLite      |
|  (Controle de Carga)  |        | (FastAPI + Uvicorn)|        |    (telemetria.db)     |
+-----------------------+        +--------------------+        +------------------------+
                                           |
                                           v
                                 +--------------------+

                                 |  Storage & Scripts |
                                 +--------------------+
```

---

## 🚀 Funcionalidades Principais

* **🔋 Gerenciamento Inteligente de Bateria (Hardware IoT):** O servidor monitora o status e temperatura da bateria e se comunica com o ESP8266 via HTTP para ligar/desligar a tomada do carregador via relé, prolongando a vida útil do dispositivo.
* **🎙️ Comandos por Voz pelo Telegram:** Envio de notas de voz no Telegram processadas por IA de transcrição (*Google Speech Recognition* + *FFmpeg* + *pydub*), executando rotinas automáticas sem dependência de chaves pagas.
* **📂 Servidor e Explorador de Arquivos:** Interface Web local e menu dinâmico no Telegram para upload, download e navegação por subpastas em `/storage`.
* **⚙️ Executor de Scripts IoT (Subprocessos Isolados):** Módulo sob demanda capaz de disparar automações e robôs Python em segundo plano sem travar a API principal.
* **📊 Dashboard de Diagnóstico:** Relatórios completos em tempo real com saúde do sistema, taxas de sucesso de rotinas, histórico de carga/temperatura e espaço em disco.
* **🚨 Telemetria & Alertas Críticos:** Notificações automáticas no Telegram em cenários de bateria fraca ou superaquecimento ($\ge 42^\circ\text{C}$).

---

## ⚡ Gerenciador de Carga Automatizado (Hardware & ESP8266)

Para evitar que o celular fique conectado à tomada 24 horas por dia estufando a bateria, o hardware monitora a carga e cicla o relé automaticamente.

### 🔌 Lógica do Ciclo de Carga

| Condição | Ação do Servidor | Resposta do ESP8266 |
| :--- | :--- | :--- |
| **Bateria $\le 20\%$** | Envia comando `{"rele": 1}` | Liga o carregador |
| **Bateria $\ge 80\%$** | Envia comando `{"rele": 0}` | Desliga o carregador |
| **Temperatura $\ge 42^\circ\text{C}$** | Emite alerta de emergência | Notifica no Telegram |

## 🖨️ Case 3D em PLA

O módulo ESP8266 acoplado ao Relé de 1 canal foi montado em um case impresso em 3D usando PLA, garantindo isolamento elétrico da rede AC, proteção dos pinos do microcontrolador e acabamento legal.

---

## 📥 Guia de Instalação e Configuração

### 1. Configurando o Termux no Android

1. Baixe o Termux atualizado via **F-Droid**.
2. Abra o Termux e atualize os repositórios base:
   ```bash
   pkg update && pkg upgrade -y
   ```
3. Instale os utilitários de sistema e codificadores de áudio:
   ```bash
   pkg install python git ffmpeg flac termux-api -y
   ```
4. Conceda as permissões de armazenamento e bateria ao Termux:
   ```bash
   termux-setup-storage
   ```
   *(Nota: Baixe o aplicativo **Termux:API** na F-Droid para permitir a leitura correta do comando `termux-battery-status`).*

### 2. Clonando e Configurando o Ambiente Python

1. Clone o repositório no seu celular:
   ```bash
   git clone https://github.com/AlanGabriel312/Gerenciador-de-Carga-e-Servidor
   cd Gerenciador-de-Carga-e-Servidor/Servidor
   ```
2. Crie e ative o ambiente virtual (`venv`):
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Instale as dependências necessárias:
   ```bash
   pip install fastapi uvicorn apscheduler python-dotenv speechrecognition pydub
   ```
4. Crie o arquivo `.env` na raiz da pasta `Servidor`:
   ```ini
   TELEGRAM_TOKEN=seu_token_aqui
   TELEGRAM_CHAT_ID=seu_chat_id_aqui
   ```

### 3. Programando o ESP8266 (PlatformIO / Arduino IDE)

Carregue o código abaixo na sua placa ESP8266 (NodeMCU / Wemos D1 Mini). Conecte o pino digital **D1** na entrada de sinal do módulo Relé.

```cpp
#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>

// ========== CONFIGURAÇÃO DE REDE ==========
const char* ssid = "NOME_DA_SUA_REDE";
const char* password = "SENHA_DA_SUA_REDE";

IPAddress local_IP(192, 168, 0, 126);
IPAddress gateway(192, 168, 0, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress primaryDNS(8, 8, 8, 8);

// Endpoint da API no servidor Termux
const char* serverUrl = "http://192.168.0.115:8000/api/comando-esp";
const int pinoRele = D1;

const unsigned long INTERVALO_CHECAGEM = 10000;
unsigned long ultimaChecagem = 0;

void checarServidorCelular() {
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClient client;
    HTTPClient http;

    http.begin(client, serverUrl);
    int httpCode = http.GET();

    if (httpCode == HTTP_CODE_OK) {
      String resposta = http.getString();
      if (resposta.indexOf("\"rele\":1") != -1) {
        digitalWrite(pinoRele, HIGH); // Liga o carregador
      }
      else if (resposta.indexOf("\"rele\":0") != -1) {
        digitalWrite(pinoRele, LOW); // Desliga o carregador
      }
    }
    http.end();
  }
}

void setup() {
  Serial.begin(9600);
  pinMode(pinoRele, OUTPUT);
  digitalWrite(pinoRele, LOW);

  WiFi.config(local_IP, gateway, subnet, primaryDNS);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

void loop() {
  if (millis() - ultimaChecagem >= INTERVALO_CHECAGEM) {
    ultimaChecagem = millis();
    checarServidorCelular();
  }
}
```

---

## 💻 Executando o Servidor

Para iniciar o servidor em segundo plano no Termux (garantindo que continue rodando mesmo se você fechar o aplicativo):

```bash
cd ~/Gerenciador-de-Carga-e-Servidor/Servidor
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

Para verificar os logs de execução em tempo real:
```bash
tail -f server.log
```

---

## 🎙️ Como Usar os Comandos por Voz (Telegram)

Basta gravar uma nota de voz no chat do bot do Telegram. O servidor tratará o texto removendo acentuações e identificará a intenção:

| Intenção | Palavras-Chave Reconhecidas | Ação Executada |
| :--- | :--- | :--- |
| **Bateria / Status** | bateria, status, energia, carga | Retorna porcentagem, conexão e temperatura atual |
| **Dashboard** | dashboard, diagnóstico, painel, relatório | Roda o diagnóstico e compila estatísticas |
| **Arquivos** | arquivo, arquivos, pasta, pastas | Abre o explorador interativo de diretórios |
| **Scripts IoT** | script, scripts, robô, robôs | Exibe menu inline para disparar scripts sob demanda |

---

## 📁 Estrutura do Repositório

```plaintext
├── Servidor/
│   ├── main.py                 # Ponto de entrada (FastAPI, Agendador e Rotas)
│   ├── telegram_bot.py         # Bot Telegram, menus e transcrição de Voz
│   ├── background_tasks.py     # Leitura de bateria e rotinas de sistema
│   ├── database.py             # Inicialização e persistência no SQLite
│   ├── executor_scripts.py     # Runner isolado de subprocessos
│   ├── dashboard_sistema.py    # Script de diagnóstico sob demanda
│   ├── scripts_iot/            # Pasta reservada para robôs e automações Python
│   └── storage/                # Servidor de arquivos (fotos, docs, áudios)
├── Hardware/
│   ├── main.cpp                # Código C++ do ESP8266 para o Relé
│   └── case_3d_esp8266.stl     # Modelo 3D da case impressa em PLA
└── README.md
```