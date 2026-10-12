"""
NexaHome Technologies — NexaSense
Gerador de firmware simulado + cálculo de hashes

Este script cria um arquivo .bin que representa o firmware educacional
do NexaSense, contendo:
  - Strings sensíveis embutidas (credenciais, endpoints, mensagens de debug)
  - Cabeçalho simulado de firmware ESP32 (ESP-IDF App Image)
  - Partições identificáveis

Depois calcula SHA-256, SHA-1 e MD5 para o registro de integridade.

EVIDÊNCIA GERADA:
  - firmware/nexasense_firmware_original.bin  (imagem simulada)
  - firmware/hashes.txt                       (atualizado com hash real)

Uso:
    python 04_firmware_generator.py
"""

import os
import struct
import hashlib
import random
from datetime import datetime

# ── Configurações embutidas no firmware (hardcoded — achados F04, F05) ─────────
STRINGS_EMBEDDED = [
    # Cabeçalho e metadados
    b"ESP-IDF v5.1.2",
    b"nexasense",
    b"0.9.1-prototype",
    b"ESP32-WROOM-32D",
    b"Sep 30 2026 10:14:22",

    # Credenciais Wi-Fi hardcoded (achado F04)
    b"NEXAHOME_WIFI_SSID=NexaHome_Lab",
    b"NEXAHOME_WIFI_PASS=Nexah0me@2026!",
    b"ssid=NexaHome_Lab",
    b"password=Nexah0me@2026!",

    # Configuração MQTT (achado F03 e F04)
    b"mqtt://192.168.1.10:1883",
    b"mqtt_user=nexasense_device",
    b"mqtt_pass=mqttP@ss123",
    b"/nexasense/device001/telemetry",
    b"/nexasense/device001/cmd",
    b"device_id=device001",
    b"client_id=device001",

    # Endpoint OTA via HTTP sem TLS (achado F05)
    b"http://192.168.1.10:8080/firmware/nexasense_latest.bin",
    b"OTA_URL=http://192.168.1.10:8080/firmware/nexasense_latest.bin",

    # Mensagens de debug verbose (achado F01 e F10)
    b"[BOOT] Starting NexaSense firmware v0.9.1-prototype",
    b"[WIFI] Connecting to SSID: %s",
    b"[WIFI] Password: %s",
    b"[WIFI] Connected! IP: %s",
    b"[MQTT] Connecting to broker: %s",
    b"[MQTT] Client ID: %s",
    b"[MQTT] Username: %s",
    b"[MQTT] Password: %s",
    b"[NVS] Loading config from NVS...",
    b"[NVS] ssid=%s password=%s",
    b"[NVS] mqtt_user=%s mqtt_pass=%s",
    b"[OTA] Starting OTA update from: %s",
    b"[OTA] OTA progress: %d%%",
    b"[SENSOR] Temp=%.1f Hum=%.1f",
    b"[ERROR] MQTT connection failed, retrying...",
    b"fw_version=0.9.1-prototype",
    b"hw_revision=ESP32-WROOM-32D",

    # Biblioteca e funções internas
    b"esp_wifi_connect",
    b"esp_mqtt_client_start",
    b"esp_https_ota",
    b"nvs_flash_init",
    b"dht_read_float_data",
    b"192.168.1.",
]


def build_esp32_app_header() -> bytes:
    """
    Monta um cabeçalho simplificado de App Image do ESP-IDF.
    Estrutura real: https://docs.espressif.com/projects/esptool/en/latest/esp32/advanced-topics/firmware-image-format.html
    """
    magic       = b'\xe9'          # magic byte ESP32
    segment_cnt = b'\x03'          # 3 segmentos
    spi_mode    = b'\x02'          # DIO
    spi_speed   = b'\x0f'          # 80 MHz
    entry_point = struct.pack('<I', 0x40080640)
    wp_pin      = b'\xee'
    reserved    = b'\x00' * 11
    return magic + segment_cnt + spi_mode + spi_speed + entry_point + wp_pin + reserved


def build_partition_table() -> bytes:
    """
    Tabela de partições simplificada (ESP32 magic 0xAA50).
    """
    entries = [
        # name        type  subtype  offset      size
        (b"nvs",       0x01, 0x02,   0x009000,   0x006000),
        (b"phy_init",  0x01, 0x01,   0x00F000,   0x001000),
        (b"factory",   0x00, 0x00,   0x010000,   0x140000),
        (b"ota_0",     0x00, 0x10,   0x150000,   0x140000),
        (b"ota_data",  0x01, 0x00,   0x290000,   0x002000),
    ]
    table = b""
    for name, t, st, offset, size in entries:
        magic  = struct.pack('<H', 0xAA50)
        typ    = struct.pack('BB', t, st)
        off    = struct.pack('<I', offset)
        sz     = struct.pack('<I', size)
        nm     = name.ljust(16, b'\x00')[:16]
        flags  = struct.pack('<I', 0)
        table += magic + typ + off + sz + nm + flags
    return table.ljust(0xC00, b'\xFF')


def build_nvs_partition() -> bytes:
    """
    Partição NVS simulada com credenciais em texto claro.
    Em um ESP32 real sem NVS Encryption, este conteúdo é extraível.
    """
    nvs_data = (
        b"NVS_PAGE_HEADER\x00" +
        b"wifi\x00ssid\x00NexaHome_Lab\x00" +
        b"wifi\x00password\x00Nexah0me@2026!\x00" +
        b"mqtt\x00broker_url\x00mqtt://192.168.1.10:1883\x00" +
        b"mqtt\x00client_id\x00device001\x00" +
        b"mqtt\x00username\x00nexasense_device\x00" +
        b"mqtt\x00password\x00mqttP@ss123\x00" +
        b"device\x00fw_version\x000.9.1-prototype\x00" +
        b"device\x00hw_revision\x00ESP32-WROOM-32D\x00"
    )
    return nvs_data.ljust(0x6000, b'\xFF')


def build_app_section() -> bytes:
    """
    Seção de aplicação com todas as strings sensíveis intercaladas com
    código binário aleatório — simulando um firmware real compilado.
    """
    sections = []

    # Preâmbulo binário (simula código compilado)
    sections.append(bytes([random.randint(0, 255) for _ in range(2048)]))

    # Intercala strings com dados aleatórios
    for s in STRINGS_EMBEDDED:
        # Preenchimento binário entre strings
        sections.append(bytes([random.randint(0, 255) for _ in range(random.randint(64, 256))]))
        sections.append(s + b'\x00')  # null-terminated como em binário real

    # Enchimento final
    app_data = b"".join(sections)
    target_size = 0x140000  # 1.3 MB — tamanho real da partição factory
    if len(app_data) < target_size:
        app_data += bytes([0xFF] * (target_size - len(app_data)))
    return app_data[:target_size]


def generate_firmware() -> bytes:
    """
    Monta a imagem completa de 4 MB (mesma estrutura do flash ESP32).
    Layout: bootloader | partition table | nvs | app
    """
    flash = bytearray(b'\xFF' * 0x400000)  # 4 MB inicialmente apagado

    # Bootloader no offset 0x0000
    bootloader = build_esp32_app_header() + b"bootloader_stage2_esp32\x00"
    bootloader = bootloader.ljust(0x8000, b'\xFF')
    flash[0x000000:0x008000] = bootloader[:0x8000]

    # Partition table no offset 0x8000
    pt = build_partition_table()
    flash[0x008000:0x008000 + len(pt)] = pt

    # NVS no offset 0x9000
    nvs = build_nvs_partition()
    flash[0x009000:0x009000 + len(nvs)] = nvs

    # App no offset 0x10000
    app = build_app_section()
    flash[0x010000:0x010000 + len(app)] = app

    return bytes(flash)


def compute_hashes(data: bytes) -> dict:
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "sha1":   hashlib.sha1(data).hexdigest(),
        "md5":    hashlib.md5(data).hexdigest(),
        "size":   len(data),
    }


def main():
    base_dir     = os.path.dirname(os.path.abspath(__file__))
    firmware_dir = os.path.join(base_dir, "..", "firmware")
    os.makedirs(firmware_dir, exist_ok=True)

    fw_path = os.path.join(firmware_dir, "nexasense_firmware_original.bin")

    print("\n" + "="*60)
    print("  NexaSense — Firmware Generator (Educacional)")
    print("="*60)
    print("\n[1/3] Gerando imagem de firmware simulada (4 MB)...")

    firmware = generate_firmware()

    print(f"[2/3] Salvando em {fw_path}...")
    with open(fw_path, "wb") as f:
        f.write(firmware)

    print("[3/3] Calculando hashes de integridade...")
    hashes = compute_hashes(firmware)

    print(f"\n{'='*60}")
    print(f"  IMAGEM GERADA COM SUCESSO")
    print(f"{'='*60}")
    print(f"  Arquivo : {os.path.basename(fw_path)}")
    print(f"  Tamanho : {hashes['size']:,} bytes ({hashes['size'] // 1024} KB)")
    print(f"  SHA-256 : {hashes['sha256']}")
    print(f"  SHA-1   : {hashes['sha1']}")
    print(f"  MD5     : {hashes['md5']}")
    print(f"{'='*60}")

    # Atualizar hashes.txt com valores reais
    hashes_path = os.path.join(firmware_dir, "hashes.txt")
    with open(hashes_path, "w", encoding="utf-8") as f:
        f.write("# =============================================================\n")
        f.write("#  NexaHome Technologies — NexaSense Firmware\n")
        f.write("#  Registro de Integridade da Imagem\n")
        f.write("# =============================================================\n\n")
        f.write(f"Arquivo           : {os.path.basename(fw_path)}\n")
        f.write(f"Versão de firmware: 0.9.1-prototype\n")
        f.write(f"Plataforma        : ESP32-WROOM-32D (simulado)\n")
        f.write(f"Framework         : ESP-IDF v5.1.2\n")
        f.write(f"Tamanho           : {hashes['size']} bytes ({hashes['size'] // 1024} KB)\n")
        f.write(f"Origem            : Gerado via 04_firmware_generator.py (ambiente sem hardware)\n")
        f.write(f"Data da geração   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"SHA-256 : {hashes['sha256']}\n")
        f.write(f"SHA-1   : {hashes['sha1']}\n")
        f.write(f"MD5     : {hashes['md5']}\n\n")
        f.write("# Partições na imagem:\n")
        f.write("# Offset 0x000000 | Bootloader\n")
        f.write("# Offset 0x008000 | Partition Table\n")
        f.write("# Offset 0x009000 | NVS (credenciais em texto claro — achado F09)\n")
        f.write("# Offset 0x010000 | App (strings sensíveis — achados F01, F04, F05)\n")
        f.write("# =============================================================\n")

    print(f"\n[✓] hashes.txt atualizado com valores reais.")
    print(f"[→] Próximo passo: execute o script 05_firmware_analysis.py")


if __name__ == "__main__":
    main()
