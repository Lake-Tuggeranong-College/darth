# DARTH

DARTH stands for "Data Acquisition for Real-time Telemetry Handler".

DARTH is a robotics and mechatronics project focused on acquiring and forwarding real-time telemetry between low-power wireless devices and a central gateway. The repository currently contains:

- a gateway running on an Adafruit Feather RP2040 RFM board with CircuitPython
- a client firmware project in C++ for a microcontroller-based node
- a simple bridge between LoRa packets and an MQTT broker for telemetry and command routing

This project is intended as a foundation for experimenting with low-power, long-range telemetry collection, downstream command delivery, and distributed monitoring in a robotics environment.

## Project overview

The current design uses a bidirectional bridge pattern:

- the gateway connects to WiFi and an MQTT broker
- the gateway receives LoRa packets from remote clients and publishes them to MQTT
- MQTT messages on a subscribed downlink topic are forwarded over LoRa to clients

This allows a local broker to act as the control and monitoring hub while the wireless devices communicate over LoRa.

## Repository layout

```text
.
├── LICENSE
├── README.md
├── .gitignore
├── client/
│   └── darthclient/
│       └── src/
│           └── main.cpp
├── gateway/
│   └── python/
│       ├── code.py
│       ├── secrets.py
│       └── lib/
│           ├── adafruit_rfm/
│           └── adafruit_minimqtt/
└── ...
```

## Hardware

The current gateway implementation targets Adafruit hardware based on the Feather RP2040 RFM board and AirLift WiFi add-on capabilities.

Typical hardware involved:

- Adafruit Feather RP2040 RFM
- Adafruit AirLift ESP32 WiFi add-on
- RFM9x LoRa radio module
- MQTT broker host on the local network
- One or more remote client nodes using the same radio configuration


## License

This project is released under the CC0 1.0 Universal license. See `LICENSE` for details.
