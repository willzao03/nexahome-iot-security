"""
NexaHome Technologies — NexaSense
Simulação do log de boot via UART (ESP32-WROOM-32D)

Este script reproduz fielmente a saída serial que apareceria
no terminal ao conectar um cabo USB ao NexaSense e apertar Reset.

EVIDÊNCIA GERADA: hardware/evidence/uart-boot-log.txt

Uso:
    python 01_uart_boot_simulation.py
    python 01_uart_boot_simulation.py --save
"""

import time
import sys
import os
import argparse
from datetime import datetime

# ── Configurações do dispositivo simulado ──────────────────────────────────────
WIFI_SSID     = "NexaHome_Lab"
WIFI_PASSWORD = "Nexah0me@2026!"          # credencial hardcoded no firmware
WIFI_IP       = "192.168.1.42"
MQTT_BROKER   = "192.168.1.10"
MQTT_PORT     = 1883
MQTT_USER     = "nexasense_device"
MQTT_PASS     = "mqttP@ss123"             # credencial hardcoded no firmware
MQTT_CLIENT   = "device001"
FW_VERSION    = "0.9.1-prototype"
HW_REVISION   = "ESP32-WROOM-32D"
# ──────────────────────────────────────────────────────────────────────────────

DELAY = 0.06  # segundos entre linhas (simula velocidade serial 115200 baud)

BOOT_LOG = f"""
ets Jul 29 2019 12:21:46

rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
configsip: 0, SPIWP:0xee
clk_drv:0x00,q_drv:0x00,d_drv:0x00,cs0_drv:0x00,hd_drv:0x00,wp_drv:0x00
mode:DIO, clock div:2
load:0x3fff0030,len:7176
load:0x40078000,len:15564
load:0x40080400,len:4
load:0x40080404,len:3904
entry 0x40080640

I (31) boot: ESP-IDF v5.1.2 2nd stage bootloader
I (31) boot: compile time Sep 30 2026 10:14:22
I (31) boot: Multicore bootloader
I (35) boot: chip revision: v3.1
I (39) boot.esp32: SPI Speed      : 80MHz
I (44) boot.esp32: SPI Mode       : DIO
I (48) boot.esp32: SPI Flash Size : 4MB
I (53) boot: Enabling RNG early entropy source...
I (58) boot: Partition Table:
I (62) boot: ## Label            Usage          Type ST    Offset   Length
I (69) boot:  0 nvs              WiFi data        01 02 00009000 00006000
I (77) boot:  1 phy_init         RF data          01 01 0000f000 00001000
I (84) boot:  2 factory          factory app      00 00 00010000 00140000
I (92) boot:  3 ota_0            OTA app          00 10 00150000 00140000
I (99) boot:  4 ota_data         OTA data         01 00 00290000 00002000
I (107) boot: End of partition table
I (111) boot: Defaulting to factory image
I (116) boot: Loading app partition at offset 0x10000
I (342) boot: Loaded app from partition at offset 0x10000
I (342) boot: Disabling RNG early entropy source...
I (362) cpu_start: Unicore app
I (362) cpu_start: Pro cpu up.
I (375) cpu_start: Pro cpu start user code
I (375) cpu_start: cpu freq: 240000000 Hz
I (375) cpu_start: Application information:
I (380) cpu_start: Project name:     nexasense
I (385) cpu_start: App version:      {FW_VERSION}
I (390) cpu_start: Compile time:     Sep 30 2026 10:14:22
I (396) cpu_start: ELF file SHA256:  a3f8c1d2e94b5706
I (402) cpu_start: ESP-IDF:          v5.1.2
I (407) cpu_start: Min chip rev:     v0.0
I (412) cpu_start: Max chip rev:     v3.99
I (417) cpu_start: Chip rev:         v3.1
I (422) heap_init: Initializing. RAM available for dynamic allocation:
I (429) heap_init: At 3FFAE6E0 len 00001920 (6 KiB): DRAM
I (435) heap_init: At 3FFB5000 len 0002B000 (172 KiB): DRAM
I (441) heap_init: At 3FFE0440 len 00003AE0 (14 KiB): D/IRAM
I (448) heap_init: At 3FFE4350 len 0001BCB0 (111 KiB): D/IRAM
I (454) heap_init: At 40094804 len 0000B7FC (45 KiB): IRAM
I (462) spi_flash: detected chip: winbond
I (465) spi_flash: flash io: dio
W (469) spi_flash: Detected size(4096k) larger than the size in the binary image header(2048k). Using the size in the binary image header.
I (483) coexist: coexist rom version 9387209
I (488) cpu_start: Starting scheduler on PRO CPU.

[BOOT] ============================================================
[BOOT] NexaSense Firmware v{FW_VERSION}
[BOOT] Hardware: {HW_REVISION}
[BOOT] ============================================================
[NVS]  Initializing NVS flash...
[NVS]  NVS initialized OK
[NVS]  Loading config from NVS...
[NVS]  ssid={WIFI_SSID} password={WIFI_PASSWORD}
[NVS]  mqtt_broker={MQTT_BROKER}:{MQTT_PORT}
[NVS]  mqtt_user={MQTT_USER} mqtt_pass={MQTT_PASS}
[NVS]  device_id={MQTT_CLIENT}
[NVS]  Config loaded OK
[WIFI] Initializing Wi-Fi stack...
[WIFI] Mode: STA
[WIFI] Connecting to SSID: {WIFI_SSID}
[WIFI] Password: {WIFI_PASSWORD}
[WIFI] .......
[WIFI] Connected!
[WIFI] IP Address : {WIFI_IP}
[WIFI] Gateway    : 192.168.1.1
[WIFI] Subnet     : 255.255.255.0
[WIFI] DNS        : 192.168.1.1
[MQTT] Initializing MQTT client...
[MQTT] Broker URI : mqtt://{MQTT_BROKER}:{MQTT_PORT}
[MQTT] Client ID  : {MQTT_CLIENT}
[MQTT] Username   : {MQTT_USER}
[MQTT] Password   : {MQTT_PASS}
[MQTT] Connecting to broker...
[MQTT] Connected to broker OK
[MQTT] Subscribed to: /nexasense/{MQTT_CLIENT}/cmd
[SENSOR] DHT22 initialized on GPIO 4
[SENSOR] First reading: Temp=24.5 Hum=62.3
[MQTT] Publishing: /nexasense/{MQTT_CLIENT}/telemetry
[MQTT] Payload: {{"device_id":"{MQTT_CLIENT}","temp":24.5,"hum":62.3,"ts":1727737200}}
[OTA]  OTA task started
[OTA]  Checking for updates at: http://{MQTT_BROKER}:8080/firmware/nexasense_latest.bin
[OTA]  No update available
[BOOT] System ready. Entering main loop...
""".strip()


def print_with_delay(text: str, delay: float, output_file=None):
    for line in text.splitlines():
        print(line)
        if output_file:
            output_file.write(line + "\n")
            output_file.flush()
        time.sleep(delay)


def main():
    parser = argparse.ArgumentParser(description="Simulação UART boot NexaSense ESP32")
    parser.add_argument("--save", action="store_true",
                        help="Salva a saída em hardware/evidence/uart-boot-log.txt")
    parser.add_argument("--fast", action="store_true",
                        help="Sem delay entre linhas (modo rápido)")
    args = parser.parse_args()

    delay = 0.0 if args.fast else DELAY

    print("\n" + "="*60)
    print("  NexaSense UART Boot Simulation")
    print("  Porta: COM3 (simulada) | Baud: 115200")
    print(f"  Data : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    time.sleep(0.5)

    # Determinar caminho de saída
    base_dir = os.path.dirname(os.path.abspath(__file__))
    evidence_dir = os.path.join(base_dir, "..", "hardware", "evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    log_path = os.path.join(evidence_dir, "uart-boot-log.txt")

    if args.save:
        with open(log_path, "w", encoding="utf-8") as f:
            header = (
                f"# NexaSense — UART Boot Log (Simulado)\n"
                f"# Data    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"# Porta   : COM3 (simulada — sem hardware físico)\n"
                f"# Baud    : 115200\n"
                f"# Analista: NexaHome Security Assessment Team\n"
                f"#\n"
                f"# NOTA DE SEGURANÇA:\n"
                f"# As linhas [NVS] abaixo revelam credenciais Wi-Fi e MQTT\n"
                f"# em texto claro — evidência do achado F01 (Risco Alto).\n"
                f"# Em um dispositivo real, qualquer pessoa com acesso físico\n"
                f"# e um cabo USB obtém estas informações em menos de 30s.\n"
                f"# =============================================================\n\n"
            )
            f.write(header)
            print_with_delay(BOOT_LOG, delay, f)
        print(f"\n[✓] Log salvo em: {log_path}")
    else:
        print_with_delay(BOOT_LOG, delay)
        print(f"\n[DICA] Execute com --save para salvar em hardware/evidence/uart-boot-log.txt")

    # Resumo do que foi evidenciado
    print("\n" + "="*60)
    print("  EVIDÊNCIAS DE SEGURANÇA IDENTIFICADAS:")
    print("="*60)
    print(f"  F01 [ALTO] Credencial Wi-Fi exposta:")
    print(f"       ssid={WIFI_SSID}  password={WIFI_PASSWORD}")
    print(f"  F01 [ALTO] Credenciais MQTT expostas:")
    print(f"       user={MQTT_USER}  pass={MQTT_PASS}")
    print(f"  F01 [MÉDIO] Device ID estático: {MQTT_CLIENT}")
    print(f"  F01 [BAIXO] Versão prototype exposta: {FW_VERSION}")
    print(f"  F05 [ALTO]  OTA via HTTP sem TLS:")
    print(f"       http://{MQTT_BROKER}:8080/firmware/nexasense_latest.bin")
    print("="*60)


if __name__ == "__main__":
    main()
