"""
NexaHome Technologies — NexaSense
Análise estática do firmware — extração de strings sensíveis

Este script replica o que ferramentas como 'strings' e 'binwalk'
fariam sobre o firmware do NexaSense, buscando:
  - Credenciais hardcoded
  - Endpoints e protocolos
  - Mensagens de debug
  - Informações de configuração
  - Dados potencialmente sensíveis

EVIDÊNCIA GERADA: firmware/analysis-notes-generated.md

Pré-requisito: executar 04_firmware_generator.py antes

Uso:
    python 05_firmware_analysis.py
    python 05_firmware_analysis.py --save
"""

import os
import re
import hashlib
import argparse
from datetime import datetime

FIRMWARE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "firmware", "nexasense_firmware_original.bin"
)

# Padrões de busca (regex sobre bytes decodificados)
PATTERNS = {
    "Credenciais Wi-Fi": [
        rb"ssid[\s=:]+\S+",
        rb"SSID[\s=:]+\S+",
        rb"WIFI[\w_]*PASS\w*[\s=:]+\S+",
        rb"password[\s=:]+\S+",
        rb"NexaHome_Lab",
        rb"Nexah0me@\S+",
    ],
    "Configuração MQTT": [
        rb"mqtt://\S+",
        rb"mqtt_\w+[\s=:]+\S+",
        rb"/nexasense/\S+",
        rb"device_id[\s=:]+\S+",
        rb"client_id[\s=:]+\S+",
    ],
    "Endpoints HTTP/OTA": [
        rb"http://\S+",
        rb"https://\S+",
        rb"OTA_URL[\s=:]+\S+",
        rb"firmware/\S+\.bin",
    ],
    "Endereços IP": [
        rb"192\.168\.\d+\.\d+",
        rb"10\.\d+\.\d+\.\d+",
        rb"172\.\d+\.\d+\.\d+",
    ],
    "Mensagens de debug": [
        rb"\[BOOT\][^\x00]+",
        rb"\[WIFI\][^\x00]+",
        rb"\[MQTT\][^\x00]+",
        rb"\[NVS\][^\x00]+",
        rb"\[OTA\][^\x00]+",
        rb"\[SENSOR\][^\x00]+",
        rb"\[ERROR\][^\x00]+",
    ],
    "Versão e metadados": [
        rb"ESP-IDF v\S+",
        rb"fw_version[\s=:]+\S+",
        rb"hw_revision[\s=:]+\S+",
        rb"\d+\.\d+\.\d+-\w+",
    ],
    "NVS (credenciais armazenadas)": [
        rb"NVS_PAGE_HEADER",
        rb"wifi\x00(ssid|password)\x00[^\x00]+",
        rb"mqtt\x00(username|password|client_id)\x00[^\x00]+",
    ],
}

# Classificação de risco por categoria
RISK_MAP = {
    "Credenciais Wi-Fi":           ("Alto",  "F04"),
    "Configuração MQTT":           ("Alto",  "F03/F04"),
    "Endpoints HTTP/OTA":          ("Alto",  "F05"),
    "Endereços IP":                ("Médio", "F03"),
    "Mensagens de debug":          ("Médio", "F01"),
    "Versão e metadados":          ("Baixo", "F10"),
    "NVS (credenciais armazenadas)":("Alto", "F09"),
}


def extract_printable_strings(data: bytes, min_len: int = 6) -> list[str]:
    """Equivalente ao comando 'strings' no Linux."""
    pattern = rb'[ -~]{' + str(min_len).encode() + rb',}'
    return [m.decode("ascii", errors="replace") for m in re.findall(pattern, data)]


def search_patterns(data: bytes) -> dict:
    results = {}
    for category, patterns in PATTERNS.items():
        found = set()
        for pat in patterns:
            matches = re.findall(pat, data, re.IGNORECASE)
            for m in matches:
                text = m.decode("utf-8", errors="replace").strip()
                if text and len(text) > 3:
                    found.add(text)
        if found:
            results[category] = sorted(found)
    return results


def identify_structure(data: bytes) -> list[dict]:
    """Identifica estruturas conhecidas (simula binwalk)."""
    structures = []

    # Magic byte do bootloader ESP32
    if data[0:1] == b'\xe9':
        structures.append({
            "offset": "0x000000",
            "description": "ESP32 Bootloader (magic byte 0xE9)",
            "risk": "Info"
        })

    # Partition table magic
    for i in range(0, min(len(data), 0x10000), 0x20):
        if data[i:i+2] == b'\x50\xAA':
            structures.append({
                "offset": f"0x{i:06X}",
                "description": "Partition Table Entry (magic 0xAA50)",
                "risk": "Info"
            })

    # Procurar por "NVS_PAGE_HEADER"
    idx = data.find(b"NVS_PAGE_HEADER")
    if idx != -1:
        structures.append({
            "offset": f"0x{idx:06X}",
            "description": "NVS Partition — credenciais em TEXTO CLARO",
            "risk": "Alto — achado F09"
        })

    # Procurar por "mqtt://"
    idx = data.find(b"mqtt://")
    if idx != -1:
        structures.append({
            "offset": f"0x{idx:06X}",
            "description": "String MQTT plaintext URL encontrada na app",
            "risk": "Alto — achado F03"
        })

    # Procurar por "http://" (OTA)
    idx = data.find(b"http://")
    if idx != -1:
        structures.append({
            "offset": f"0x{idx:06X}",
            "description": "String HTTP URL (OTA sem TLS) encontrada na app",
            "risk": "Alto — achado F05"
        })

    return structures


def main():
    parser = argparse.ArgumentParser(description="Análise estática do firmware NexaSense")
    parser.add_argument("--save", action="store_true",
                        help="Salva análise em firmware/analysis-notes-generated.md")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  NexaSense — Firmware Static Analysis")
    print("  Equivalente a: binwalk + strings")
    print("="*60)

    if not os.path.exists(FIRMWARE_PATH):
        print(f"\n[ERRO] Firmware não encontrado: {FIRMWARE_PATH}")
        print("       Execute primeiro: python 04_firmware_generator.py")
        return

    print(f"\n[1/4] Carregando firmware: {os.path.basename(FIRMWARE_PATH)}")
    with open(FIRMWARE_PATH, "rb") as f:
        data = f.read()

    size = len(data)
    sha256 = hashlib.sha256(data).hexdigest()
    print(f"       Tamanho : {size:,} bytes ({size // 1024} KB)")
    print(f"       SHA-256 : {sha256}")

    print("\n[2/4] Identificando estruturas (binwalk)...")
    structures = identify_structure(data)
    for s in structures:
        print(f"       {s['offset']}  {s['description']}")
        if s['risk'] != "Info":
            print(f"                ⚠ Risco: {s['risk']}")

    print("\n[3/4] Extraindo strings sensíveis (strings + grep)...")
    pattern_results = search_patterns(data)

    all_lines = []
    for category, strings in pattern_results.items():
        risk, finding = RISK_MAP.get(category, ("Desconhecido", "?"))
        print(f"\n  [{risk}] {category} (Achado {finding})")
        for s in strings:
            display = s if len(s) <= 80 else s[:77] + "..."
            print(f"    → {display}")
            all_lines.append((category, risk, finding, display))

    print("\n[4/4] Extração geral de strings (primeiras 30 únicas > 10 chars)...")
    all_strings = extract_printable_strings(data, min_len=10)
    unique_strings = sorted(set(all_strings))[:30]
    for s in unique_strings:
        print(f"    {s}")

    # Salvar evidência
    if args.save:
        base_dir     = os.path.dirname(os.path.abspath(__file__))
        firmware_dir = os.path.join(base_dir, "..", "firmware")
        path = os.path.join(firmware_dir, "analysis-notes-generated.md")

        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Análise de Firmware — NexaSense (Gerado Automaticamente)\n\n")
            f.write(f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
            f.write(f"**Arquivo:** {os.path.basename(FIRMWARE_PATH)}  \n")
            f.write(f"**Tamanho:** {size:,} bytes  \n")
            f.write(f"**SHA-256:** `{sha256}`  \n\n")
            f.write("---\n\n## Estruturas Identificadas (binwalk)\n\n")
            f.write("| Offset | Descrição | Risco |\n|--------|-----------|-------|\n")
            for s in structures:
                f.write(f"| `{s['offset']}` | {s['description']} | {s['risk']} |\n")

            f.write("\n---\n\n## Strings Sensíveis Encontradas\n\n")
            for category, strings in pattern_results.items():
                risk, finding = RISK_MAP.get(category, ("?", "?"))
                f.write(f"\n### [{risk}] {category} — Achado {finding}\n\n")
                f.write("```\n")
                for s in strings:
                    f.write(f"{s}\n")
                f.write("```\n")

        print(f"\n[✓] Análise salva em: {path}")
    else:
        print(f"\n[DICA] Execute com --save para salvar a análise completa.")

    print(f"\n{'='*60}")
    print(f"  RESUMO: {len(all_lines)} strings sensíveis encontradas")
    print(f"  Firmware analisado sem criptografia — Flash Encryption AUSENTE")
    print(f"  → Qualquer ferramenta (binwalk, strings) acessa o conteúdo")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
