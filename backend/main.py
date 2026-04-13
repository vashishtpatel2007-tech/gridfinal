from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json
import paho.mqtt.client as mqtt
import ssl
import random 

# ============================================================
# 🚨 CONFIGURATION: YOUR HIVEMQ DETAILS
# ============================================================
MQTT_BROKER = "33237a7f42cf452096a50ed8bd769195.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "gridsync_admin"
MQTT_PASS = "1928Vasu"

TOPIC_COMMANDS = "gridsync/commands"
TOPIC_TELEMETRY = "gridsync/telemetry"

app = FastAPI()

# Enable CORS (Allows browser to talk to server easily)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ⚠️ MAKE SURE THIS FOLDER EXISTS: backend/templates
templates = Jinja2Templates(directory="backend/templates")

# --- GLOBAL STATE (Memory) ---
current_grid_state = {"status": "NORMAL", "deficit_mw": 0}

# 💰 WALLET CONFIGURATION (New Addition)
user_wallet_balance = 45.00 

# ============================================================
# 1. MQTT CLIENT (The "Brain" Connection)
# ============================================================
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ SUCCESS: Python is Connected to HiveMQ Cloud!")
        client.subscribe(TOPIC_TELEMETRY)
    else:
        print(f"❌ Connection Failed. Error Code: {rc}")

def on_message(client, userdata, msg):
    print(f"📩 MQTT MSG: {msg.topic} -> {msg.payload.decode()}")

# --- CRITICAL FIX: Random ID prevents 'Stuttering' Disconnects ---
client_id = f"GridSync_Server_{random.randint(1, 100000)}"
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id)
# ----------------------------------------------------------------

mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
mqtt_client.tls_set(cert_reqs=ssl.CERT_NONE)
mqtt_client.tls_insecure_set(True)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

print(f"🔌 Connecting to HiveMQ as {client_id}...")
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# ============================================================
# 2. WEBSOCKET MANAGER (Real-time updates to Screens)
# ============================================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # Sends data to ALL connected screens (Admin, User, BESCOM)
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# ============================================================
# 3. WEBPAGES (HTML Routes)
# ============================================================
@app.get("/bescom")
def get_bescom(request: Request):
    return templates.TemplateResponse("bescom.html", {"request": request})

@app.get("/admin")
def get_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/user")
def get_user(request: Request):
    return templates.TemplateResponse("user.html", {"request": request})

@app.get("/dashboard") # Fallback link
def get_dashboard(request: Request):
    return templates.TemplateResponse("user.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep connection open
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ============================================================
# 4. API ENDPOINTS (The Logic)
# ============================================================

# --- BESCOM ALERT LISTENER (Triggered by Graph > 85%) ---
class GridUpdate(BaseModel):
    load: int

@app.post("/api/bescom/auto-alert")
async def receive_auto_alert(update: GridUpdate):
    """
    1. Receives 'High Load' alert from BESCOM Frontend.
    2. Updates Admin Screen to show the 'Approve' button.
    """
    print(f"🚨 ALERT RECEIVED FROM SIMULATOR: {update.load} MW")
    
    current_grid_state["status"] = "CRITICAL"
    current_grid_state["deficit_mw"] = update.load
    
    # Notify Admin Screen immediately
    await manager.broadcast({
        "type": "GRID_ALERT", 
        "msg": f"⚠️ CRITICAL SURGE: {update.load} MW Detected",
        "mw": update.load
    })
    return {"status": "Alert Sent to Admin"}

# --- ADMIN ACTION: APPROVE LOAD SHED ---
@app.post("/api/admin/approve")
async def admin_approve():
    """
    Triggered when Admin clicks 'APPROVE DROP'.
    1. Sends 'ECO_MODE' to Hardware (Blue Light ON).
    2. Updates User Screen (Money Earned).
    """
    global user_wallet_balance # Access the global money variable
    
    print("✅ ADMIN APPROVED. Sending ECO_MODE to ESP32...")
    
    # 1. Send MQTT Command to Hardware (ESP32)
    mqtt_client.publish(TOPIC_COMMANDS, "ECO_MODE")
    
    # 2. ADD MONEY (The Incentive)
    user_wallet_balance += 5.00
    print(f"💰 Wallet Updated: ₹{user_wallet_balance}")

    # 3. Update Web Screens
    current_grid_state["status"] = "STABILIZING"
    await manager.broadcast({
        "type": "ECO_ACTIVATED", 
        "msg": "✅ Load Shedding Active. Grid Stabilizing.",
        "new_balance": user_wallet_balance
    })
    
    return {"status": "Command Sent", "new_balance": user_wallet_balance}

# --- NEW: USER STATS ENDPOINT (For the Dashboard) ---
@app.get("/api/user-stats")
async def get_user_stats():
    global user_wallet_balance
    return {
        "earnings": user_wallet_balance,
        "status": "Eco Mode Active"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)