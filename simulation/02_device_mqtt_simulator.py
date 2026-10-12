"""
NexaHome Technologies — NexaSense
Simulação do dispositivo IoT publicando telemetria via MQTT

Uso:
    python 02_device_mqtt_simulator.py
    python 02_device_mqtt_simulator.py --count 10
"""

import paho.mqtt.client as mqtt
import json, time, random, argparse, os
from datetime import datetime, timezone

BROKER_HOST = "localhost"
BROKER_PORT = 1883
MQTT_USER   = "nexasense_device"
MQTT_PASS   = "mqttP@ss123"
CLIENT_ID   = "device001"
TOPIC_PUB   = f"/nexasense/{CLIENT_ID}/telemetry"
TOPIC_SUB   = f"/nexasense/{CLIENT_ID}/cmd"

temp_base = 24.5
hum_base  = 62.0


def build_payload():
    global temp_base, hum_base
    temp_base = max(18.0, min(35.0, temp_base + random.uniform(-0.3, 0.3)))
    hum_base  = max(30.0, min(95.0, hum_base  + random.uniform(-0.5, 0.5)))
    return {
        "device_id": CLIENT_ID,
        "temp": round(temp_base, 1),
        "hum":  round(hum_base, 1),
        "ts":   int(datetime.now(timezone.utc).timestamp()),
    }


def save_evidence(payloads):
    base   = os.path.dirname(os.path.abspath(__file__))
    ev_dir = os.path.join(base, "..", "network", "evidence")
    os.makedirs(ev_dir, exist_ok=True)
    path = os.path.join(ev_dir, "mqtt-telemetry-payload.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# NexaSense - Payloads MQTT capturados\n")
        f.write(f"# Data   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Broker : {BROKER_HOST}:{BROKER_PORT} (sem TLS -- achado F03)\n")
        f.write(f"# Topico : {TOPIC_PUB}\n")
        f.write(f"# User   : {MQTT_USER} / Pass: {MQTT_PASS}  (hardcoded -- achado F04)\n")
        f.write("#\n# NOTA: No Wireshark use filtro 'mqtt' para ver estes pacotes.\n")
        f.write("# O broker nao exige autenticacao (achado F06 -- allow_anonymous).\n\n")
        for i, p in enumerate(payloads, 1):
            f.write(f"#{i:03d} [{p['ts_str']}] Topico: {TOPIC_PUB}\n")
            f.write(f"       Payload : {json.dumps(p['payload'])}\n")
            f.write(f"       TLS     : NENHUMA\n\n")
    print(f"[OK] Evidencia salva: {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count",    type=int, default=8)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()

    print("\n" + "="*55)
    print("  NexaSense - Device MQTT Simulator")
    print(f"  Broker  : {BROKER_HOST}:{BROKER_PORT}  (SEM TLS)")
    print(f"  Cliente : {CLIENT_ID}")
    print(f"  Usuario : {MQTT_USER}")
    print(f"  Senha   : {MQTT_PASS}  (hardcoded -- achado F04)")
    print("="*55 + "\n")

    # Client ID unico para evitar conflito no broker
    sim_cid = f"{CLIENT_ID}_sim_{random.randint(10000, 99999)}"

    conn_ok  = [False]
    disc_ok  = [False]

    def on_connect(c, u, f, rc, p=None):
        v = rc.value if hasattr(rc, 'value') else int(rc)
        if v == 0:
            conn_ok[0] = True
            print(f"[MQTT] Conectado  : {BROKER_HOST}:{BROKER_PORT}")
            print(f"[MQTT] Client ID  : {CLIENT_ID} (sim: {sim_cid})")
            print(f"[MQTT] Broker aceita conexao anonima -- achado F06")
            c.subscribe(TOPIC_SUB, qos=0)
        else:
            print(f"[MQTT] Falha rc={v}")

    def on_disconnect(c, u, *args_):
        disc_ok[0] = True

    def on_message(c, u, msg):
        try:
            data = json.loads(msg.payload.decode())
            print(f"\n[CMD] Comando recebido: {json.dumps(data)}")
        except Exception:
            print(f"\n[CMD] {msg.payload.decode()}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=sim_cid)
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message

    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    except ConnectionRefusedError:
        print("[ERRO] Broker nao encontrado. Inicie o Mosquitto primeiro.")
        return

    client.loop_start()

    # Aguardar conexao
    for _ in range(50):
        time.sleep(0.1)
        if conn_ok[0]:
            break
    else:
        print("[ERRO] Timeout aguardando conexao com o broker.")
        client.loop_stop()
        return

    time.sleep(0.3)
    print(f"\n[SENSOR] Publicando {args.count} mensagem(ns)...\n")

    saved = []
    for i in range(1, args.count + 1):
        if disc_ok[0]:
            print("[AVISO] Desconectado do broker.")
            break

        payload     = build_payload()
        payload_str = json.dumps(payload)
        ts_str      = datetime.now().strftime("%H:%M:%S")

        client.publish(TOPIC_PUB, payload_str, qos=0)

        print(f"[MQTT] #{i:03d} [{ts_str}] -> {TOPIC_PUB}")
        print(f"       Payload : {payload_str}")
        print(f"       TLS     : NENHUMA (achado F03)\n")

        saved.append({"ts_str": ts_str, "payload": payload})

        if i < args.count:
            time.sleep(args.interval)

    time.sleep(0.5)
    client.loop_stop()

    # Salvar evidencia independente de quantas mensagens saíram
    if saved:
        save_evidence(saved)

    print(f"\n[OK] {len(saved)} mensagem(ns) publicada(s).")
    print(f"[!]  Qualquer cliente na rede poderia ter lido estas mensagens.")


if __name__ == "__main__":
    main()
