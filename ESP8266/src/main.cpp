#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>

// ========== DADOS DO WI-FI ==========
const char* ssid = "Multiplay-Roteador";
const char* password = "20202290";

// ========== CONFIGURAÇÃO DE IP FIXO ==========
// Ajustado para o IP que o seu aplicativo espera (192.168.0.126)
IPAddress local_IP(192, 168, 0, 126);
// Gateway do seu roteador (geralmente .1 ou .254 - ajuste se necessário)
IPAddress gateway(192, 168, 0, 1);
// Máscara de sub-rede padrão
IPAddress subnet(255, 255, 255, 0);
// DNS primário (pode usar o do Google ou o do seu roteador)
IPAddress primaryDNS(8, 8, 8, 8);   

ESP8266WebServer server(80);

const int pinoRele = D1;

// Função que processa os dados de bateria enviados pelo MIT App Inventor
void atualizarBateria() {
  // Verifica se o aplicativo enviou o parâmetro "nivel"
  if (server.hasArg("nivel")) {
    String nivelString = server.arg("nivel");
    int nivelBateria = nivelString.toInt(); // Converte o texto recebido para número inteiro

    Serial.print("Bateria do Smartphone recebida: ");
    Serial.print(nivelBateria);
    Serial.println("%");

    // LÓGICA DE DECISÃO DO GERENCIADOR DE CARGA
    if (nivelBateria <= 20) {
      digitalWrite(pinoRele, HIGH);
      Serial.println(">> BATERIA BAIXA (<=20%). Ligando o carregador...");
      server.send(200, "text/plain", "CARREGADOR_LIGADO");
    } 
    else if (nivelBateria >= 80) {
      digitalWrite(pinoRele, LOW);
      Serial.println(">> BATERIA SUFICIENTE (>=80%). Desligando para proteger...");
      server.send(200, "text/plain", "CARREGADOR_DESLIGADO");
    } 
    else {
      Serial.println(">> Bateria em nível intermediário. Mantendo estado atual.");
      server.send(200, "text/plain", "ESTADO_MANTIDO");
    }
  } else {
    server.send(400, "text/plain", "Erro: parametro 'nivel' nao encontrado");
  }
}

void setup() {
  Serial.begin(9600);
  delay(1000);

  pinMode(pinoRele, OUTPUT);
  digitalWrite(pinoRele, LOW); // Começa desligado por segurança

  // Configura o IP estático antes de iniciar o Wi-Fi
  if (!WiFi.config(local_IP, gateway, subnet, primaryDNS)) {
    Serial.println("Falha ao configurar o IP estático!");
  }

  Serial.print("Conectando em: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("Wi-Fi Conectado com sucesso!");
  Serial.print("Endereço IP fixo do seu ESP8266: ");
  Serial.println(WiFi.localIP());

  // Define que quando o celular acessar "/bateria", vai rodar a função acima
  server.on("/bateria", atualizarBateria);

  server.begin();
  Serial.println("Servidor de Carga Iniciado.");
}

void loop() {
  server.handleClient();
}