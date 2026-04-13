#include <WiFi.h>
#include <PubSubClient.h>
#include <WiFiClientSecure.h> // <--- YOU MUST HAVE THIS LINE

// ============================================================
// 🚨 CONFIGURATION: ENTER YOUR DETAILS HERE 🚨
// ============================================================

// 1. WiFi Details
const char* ssid = "Airtel_AirFi";        // Your Home WiFi Name
const char* password = "1qaz2wsx"; // Your Home WiFi Password

// 2. HiveMQ Details (SAME as your Python Code)
const char* mqtt_server = "33237a7f42cf452096a50ed8bd769195.s1.eu.hivemq.cloud"; 
const int mqtt_port = 8883; // Secure Port
const char* mqtt_user = "gridsync_admin";
const char* mqtt_pass = "1928Vasu";

// ============================================================

// Pins
const int RELAY_PIN = 23;  // The pin we connect the Relay to (D23)
const int LED_PIN = 2;     // Built-in LED on the board

WiFiClientSecure espClient;
PubSubClient client(espClient);

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  
  // Start with Fan ON (Normal Mode)
  digitalWrite(RELAY_PIN, LOW); 

  // 1. Connect to WiFi
  setup_wifi();

  // 2. Configure MQTT (Secure)
  espClient.setInsecure(); // Skip certificate validation (easier for hackathons)
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
}

// --- WiFi Connection ---
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("✅ WiFi connected");
}

// --- MQTT Reconnect Logic ---
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      Serial.println("connected");
      // Subscribe to Commands
      client.subscribe("gridsync/commands");
      Serial.println("✅ Listening for commands on 'gridsync/commands'");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

// --- THE LOGIC: What happens when Python sends a command ---
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);

  // Check if the command is "ECO_MODE"
  // Note: We are doing a simple string check. In real life we parse JSON.
  if (message.indexOf("ECO_MODE") > 0) {
    Serial.println("⚠️ COMMAND RECEIVED: ACTIVATE ECO MODE");
    
    // TURN OFF THE RELAY (Fan stops/slows)
    digitalWrite(RELAY_PIN, HIGH);
    digitalWrite(LED_PIN, HIGH); // Turn on on-board LED to show status
    
    // Send confirmation back to Python
    char telemetry[] = "{\"device_id\": \"ESP32_01\", \"status\": \"ECO_ON\", \"temp\": 26}";
    client.publish("gridsync/telemetry", telemetry);
    
    // Wait for demo duration (e.g., 5 seconds) then reset
    delay(5000); 
    
    // Reset to Normal
    digitalWrite(RELAY_PIN, LOW);
    digitalWrite(LED_PIN, LOW);
    Serial.println("✅ Reset to Normal Mode");
  }
}