#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>

// ========== DADOS DO WI-FI ==========
const char* ssid = "Multiplay-Roteador";
const char* password = "20202290";

// ========== CONFIGURAÇÃO DE IP FIXO ==========
IPAddress local_IP(192, 168, 0, 126);
IPAddress gateway(192, 168, 0, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress primaryDNS(8, 8, 8, 8);   

// ========== URL DA API NO SERVIDOR CELULAR ==========
const char* serverUrl = "http://192.168.0.115:8000/api/comando-esp";

const int pinoRele = D1;

// Intervalo de consulta (a cada 10 segundos)
const unsigned long INTERVALO_CHECAGEM = 10000;
unsigned long ultimaChecagem = 0;

void checarServidorCelular() {
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClient client;
    HTTPClient http;

    Serial.print("Consultando servidor no celular... ");
    http.begin(client, serverUrl);
    
    int httpCode = http.GET(); // Faz a requisição GET para a API do FastAPI

    if (httpCode == HTTP_CODE_OK) {
      String resposta = http.getString();
      Serial.print("Resposta recebida: ");
      Serial.println(resposta);

      // Busca simples na string JSON para ligar/desligar o relé
      if (resposta.indexOf("\"rele\":1") != -1) {
        digitalWrite(pinoRele, HIGH);
        Serial.println(">> LIGANDO O CARREGADOR (Relé HIGH)");
      } 
      else if (resposta.indexOf("\"rele\":0") != -1) {
        digitalWrite(pinoRele, LOW);
        Serial.println(">> DESLIGANDO O CARREGADOR (Relé LOW)");
      } 
      else {
        Serial.println(">> Nível dentro da margem. Mantendo estado atual.");
      }
    } else {
      Serial.printf("Erro na requisição HTTP: %d\n", httpCode);
    }
    http.end();
  } else {
    Serial.println("Wi-Fi desconectado!");
  }
}

void setup() {
  Serial.begin(9600);
  delay(1000);

  pinMode(pinoRele, OUTPUT);
  digitalWrite(pinoRele, LOW); // Começa desligado por segurança

  // Configura o IP estático
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
  Serial.print("Endereço IP fixo do ESP8266: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  unsigned long tempoAtual = millis();
  
  // Consulta o celular periodicamente a cada 10s
  if (tempoAtual - ultimaChecagem >= INTERVALO_CHECAGEM) {
    ultimaChecagem = tempoAtual;
    checarServidorCelular();
  }
}