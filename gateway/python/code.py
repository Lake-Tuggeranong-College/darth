import time
import board
import busio
import digitalio
import adafruit_connection_manager
import adafruit_rfm9x
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_esp32spi import adafruit_esp32spi

# --- SOCKET IMPORT FOR CIRCUITPYTHON 9.x / 10.x ---
try:
    from adafruit_esp32spi import adafruit_esp32spi_socketpool as socket
except ImportError:
    try:
        import adafruit_esp32spi_socketpool as socket
    except ImportError:
        try:
            from adafruit_esp32spi import adafruit_esp32spi_socket as socket
        except ImportError:
            print("Error: Neither socketpool nor socket module found in lib/adafruit_esp32spi!")
            raise

# --- CONFIGURATION ---
WIFI_SSID = "gogogadgetnodes"
WIFI_PASS = "st@rw@rs"
MQTT_BROKER = "192.168.68.107"
MQTT_PORT = 6683  # Custom MQTT Broker Port
MQTT_UPLINK_TOPIC = "lora/gateway/data"
MQTT_DOWNLINK_TOPIC = "modules/client"
RADIO_FREQ_MHZ = 915.0


# --- HARDWARE INITIALIZATION ---
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)

# AirLift Wing SPI Pinout
esp32_cs = digitalio.DigitalInOut(board.D13)
esp32_ready = digitalio.DigitalInOut(board.D11)
esp32_reset = digitalio.DigitalInOut(board.D12)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

# RFM9x LoRa Setup
rfm9x_cs = digitalio.DigitalInOut(board.RFM_CS)
rfm9x_reset = digitalio.DigitalInOut(board.RFM_RST)
rfm9x = adafruit_rfm9x.RFM9x(spi, rfm9x_cs, rfm9x_reset, RADIO_FREQ_MHZ)
rfm9x.tx_power = 23

# Sync word - to distinguish this project, and filter out other projects comms.
rfm9x.sync_word = 0xDA


# --- NETWORK CONNECTION ---
print("Connecting to WiFi...")
while not esp.is_connected:
    try:
        esp.connect_AP(WIFI_SSID, WIFI_PASS)
    except Exception as e:
        print("WiFi connection failed, retrying...", e)
        esp32_reset.value = False
        time.sleep(0.1)
        esp32_reset.value = True
        time.sleep(1)
        continue
print("Connected to WiFi!")

# --- MQTT SETUP & CALLBACKS ---
pool = adafruit_connection_manager.get_radio_socketpool(esp)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(esp)

mqtt_client = MQTT.MQTT(
    broker=MQTT_BROKER,
    port=MQTT_PORT,
    client_id="LoRaGateway_CircuitPython",
    socket_pool=pool,
    ssl_context=ssl_context
)

def message_handler(client, topic, message):
    """Triggered when a downlink message arrives from the MQTT broker."""
    print(f"[MQTT RX] Topic: '{topic}' | Payload: '{message}'")
    
    # Broadcast message down to LoRa Client nodes
    payload_bytes = bytes(message, "utf-8")
    rfm9x.send(payload_bytes)
    print(f"[LoRa TX] Forwarded downlink message over LoRa: '{message}'")

# Register MQTT callback handlers
mqtt_client.on_message = message_handler

def connect_mqtt():
    """Connects to MQTT broker and subscribes to downlink topic."""
    if mqtt_client.is_connected():
        return True
    
    print("Connecting to MQTT broker...")
    try:
        mqtt_client.connect()
        # Subscribe to downlink topic upon successful connection
        mqtt_client.subscribe(MQTT_DOWNLINK_TOPIC)
        print(f"Connected to MQTT! Subscribed to topic: '{MQTT_DOWNLINK_TOPIC}'")
        return True
    except Exception as e:
        print("MQTT connection failed:", e)
        return False

connect_mqtt()

# --- MAIN GATEWAY LOOP ---
print("Gateway active. Bi-directional LoRa <-> MQTT bridge running...")

while True:
    try:
        if not mqtt_client.is_connected():
            if not connect_mqtt():
                time.sleep(2)
                continue

        # 1. Process MQTT keepalives & incoming downlink messages
        try:
            mqtt_client.loop()
        except Exception as loop_err:
            print("MQTT loop ping error:", loop_err)

        # 2. Check for incoming uplink LoRa packets from Client
        packet = rfm9x.receive(timeout=0.5)
        
        if packet is not None:
            try:
                packet_text = str(packet, "utf-8")
                rssi = rfm9x.last_rssi
                print(f"[LoRa RX] RSSI {rssi} dBm | Uplink Data: {packet_text}")
                
                # Forward uplink payload to MQTT broker
                if mqtt_client.is_connected():
                    mqtt_client.publish(MQTT_UPLINK_TOPIC, packet_text)
                    print(f"[MQTT TX] Published to topic '{MQTT_UPLINK_TOPIC}'")
            except (UnicodeError, ValueError):
                print("Garbled LoRa packet received")

    except Exception as e:
        print("Main loop error:", e)
        time.sleep(2)