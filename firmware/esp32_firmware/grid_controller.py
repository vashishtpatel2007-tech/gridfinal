import time
import random
import json
import paho.mqtt.client as mqtt
import ssl

# ==========================================
# 🚨 CONFIGURATION (Matches your ESP32)
# ==========================================
MQTT_BROKER = "33237a7f42cf452096a50ed8bd769195.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "gridsync_admin"
MQTT_PASS = "1928Vasu"

# Topics
TOPIC_COMMANDS = "gridsync/commands"
TOPIC_TELEMETRY = "gridsync/telemetry"

# ==========================================
# 1. SETUP MQTT CONNECTION
# ==========================================
def on_connect(client, userdata, flags, rc, properties=None): # Updated signature for v2
    if rc == 0:
        print("✅ CONNECTED to HiveMQ Cloud!")
        client.subscribe(TOPIC_TELEMETRY)
    else:
        print(f"❌ Connection Failed. Error Code: {rc}")

def on_message(client, userdata, msg):
    # This listens for the confirmation from ESP32
    print(f"📩 FEEDBACK from Device: {msg.payload.decode()}")

# --- FIX: We must specify CallbackAPIVersion.VERSION2 for the new library ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "Grid_Controller_Python")
# ---------------------------------------------------------------------------

client.username_pw_set(MQTT_USER, MQTT_PASS)

# SECURE CONNECTION (Required for HiveMQ Cloud)
client.tls_set(cert_reqs=ssl.CERT_NONE) 
client.tls_insecure_set(True)

client.on_connect = on_connect
client.on_message = on_message

print("🔌 Connecting to Grid Network...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start() # Run network loop in background

# ==========================================
# 2. THE MAIN LOOP (The "Brain")
# ==========================================
try:
    while True:
        # Simulate Grid Load (0% to 100%)
        # In a real hackathon, this would come from an API or a slider
        grid_load = random.randint(40, 95) 
        
        print(f"\n📊 Current Grid Load: {grid_load}%")

        if grid_load > 85:
            print("🚨 HIGH LOAD DETECTED! Sending ECO_MODE signal...")
            client.publish(TOPIC_COMMANDS, "ECO_MODE")
            print("📡 Signal Sent. Waiting for load to drop...")
            
            # Wait 10 seconds before checking again (to give device time to react)
            time.sleep(10)
            
        else:
            print("✅ Grid is Stable.")
            time.sleep(2) # Check every 2 seconds

except KeyboardInterrupt:
    print("\n🛑 Stopping Grid Controller.")
    client.loop_stop()
    client.disconnect()