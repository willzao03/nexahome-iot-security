# NexaHome IoT Security Assessment
## Avaliação de Segurança — NexaSense (ESP32)

> **Escopo:** Avaliação educacional realizada sobre dispositivo de laboratório autorizado.  
> Nenhum teste foi realizado contra redes de produção, serviços externos ou dispositivos de terceiros.

---

## 1. Objetivo da Avaliação

Realizar uma avaliação de segurança estruturada do protótipo NexaSense — dispositivo IoT baseado em ESP32 que coleta temperatura e umidade e transmite dados via Wi-Fi para uma plataforma de monitoramento — identificando superfícies de ataque, classificando riscos e propondo medidas de hardening antes da implantação comercial.

---

## 2. Dispositivo Analisado

| Campo                  | Valor                                      |
|------------------------|--------------------------------------------|
| **Produto**            | NexaSense v0.9 (protótipo)                 |
| **Microcontrolador**   | ESP32-WROOM-32D (Xtensa LX6 dual-core)     |
| **Memória Flash**      | 4 MB SPI Flash (W25Q32)                    |
| **Sensores**           | DHT22 (temperatura e umidade)              |
| **Conectividade**      | Wi-Fi 802.11 b/g/n (2,4 GHz)              |
| **Interfaces físicas** | UART0 (USB-Serial CP2102), pinos JTAG expostos, SPI, I²C |
| **Alimentação**        | 5 V via USB / 3,3 V regulado interno       |
| **Firmware**           | ESP-IDF v5.1 — build educacional           |
| **Protocolo de rede**  | MQTT (sem TLS) sobre TCP/IP                |
| **OTA**                | HTTP OTA (sem verificação de assinatura)   |

---

## 3. Limites e Escopo dos Testes

- **Incluído:** firmware educacional fornecido, interface UART, tráfego MQTT na rede de laboratório isolada, análise estática do binário.  
- **Excluído:** redes de produção, dispositivos de terceiros, serviços externos, exploração de sistemas fora do laboratório.  
- **Não realizado:** programação irreversível de eFuses, habilitação permanente de Secure Boot / Flash Encryption no dispositivo.  
- **Ferramentas utilizadas em ambiente isolado:** esptool.py, binwalk, strings, Wireshark/tcpdump, Python 3, screen/minicom.

---

## 4. Arquitetura

```
[DHT22]
   │
   ▼
[ESP32-WROOM-32D]
   ├── Firmware (ESP-IDF) ──── Flash SPI (4 MB)
   ├── UART0 ────────────────── USB-Serial (CP2102)  ← debug exposto
   ├── JTAG (GPIO 12-15) ────── pinos acessíveis     ← debug exposto
   └── Wi-Fi 802.11n
          │
          ▼
   [Rede de laboratório 192.168.1.0/24]
          │
          ▼
   [Broker MQTT — Mosquitto 192.168.1.10:1883]  ← sem TLS, sem autenticação
          │
          ▼
   [Plataforma de monitoramento]
```

Diagrama visual completo: [`architecture/architecture-diagram.png`](architecture/architecture-diagram.png)

---

## 5. Ferramentas Utilizadas

| Ferramenta      | Versão  | Finalidade                                     |
|-----------------|---------|------------------------------------------------|
| esptool.py      | 4.7.0   | Extração da imagem de firmware via UART        |
| binwalk         | 2.3.4   | Identificação de estrutura e partições         |
| strings         | GNU     | Extração de strings do binário                 |
| Wireshark       | 4.2.x   | Captura e análise do tráfego MQTT              |
| screen / minicom| —       | Monitoramento da saída UART                    |
| Python 3        | 3.11    | Scripts auxiliares de análise                  |
| sha256sum       | GNU     | Geração de hashes para integridade             |

---

## 6. Organização das Evidências

```
nexahome-iot-security/
├── README.md                        ← este arquivo
├── architecture/
│   └── architecture-diagram.png     ← diagrama visual da arquitetura
├── firmware/
│   ├── hashes.txt                   ← hashes SHA-256 da imagem original
│   └── analysis-notes.md            ← análise estática do firmware
├── hardware/
│   ├── interface-map.md             ← mapeamento das interfaces físicas
│   └── evidence/                    ← fotos / capturas das interfaces
├── network/
│   ├── protocol-analysis.md         ← análise do tráfego MQTT
│   └── evidence/                    ← capturas Wireshark (.pcapng)
├── findings/
│   └── findings.md                  ← tabela de achados e riscos
└── remediation/
    └── hardening-plan.md            ← plano de hardening
```

---

## 7. Resumo da Análise de Firmware

- Imagem de 4 MB extraída via `esptool.py` pela interface UART sem autenticação.
- Binwalk identificou partições: bootloader, partition table, nvs, app (ESP-IDF).
- `strings` revelou: SSID e senha Wi-Fi em texto claro, endpoint MQTT (`mqtt://192.168.1.10:1883`), topic `/nexasense/device001/telemetry`, mensagens de debug verbose, credenciais MQTT sem criptografia.
- Sem verificação de assinatura no mecanismo OTA (HTTP puro).

Detalhes completos: [`firmware/analysis-notes.md`](firmware/analysis-notes.md)

---

## 8. Resumo da Análise de Hardware

- UART0 acessível fisicamente sem proteção; expõe log completo de boot com informações sensíveis (SSID, IP, versão de firmware, estado interno).
- Pinos JTAG (GPIO 12, 13, 14, 15) acessíveis na placa; JTAG não desabilitado via eFuse.
- Chip de flash SPI (W25Q32) sem Flash Encryption; conteúdo legível diretamente.
- Sem evidência de proteção física (epoxy, tamper seal) no protótipo.

Detalhes completos: [`hardware/interface-map.md`](hardware/interface-map.md)

---

## 9. Resumo da Análise dos Protocolos

- Protocolo: MQTT 3.1.1 sobre TCP porta 1883 (sem TLS).
- Broker Mosquitto configurado sem autenticação (`allow_anonymous true`).
- Payload JSON transmitido em texto claro: `{"device_id":"device001","temp":24.5,"hum":62.3,"ts":1727737200}`.
- Qualquer cliente na rede pode publicar ou assinar qualquer tópico.
- Sem mecanismo de integridade ou autenticação das mensagens.

Detalhes completos: [`network/protocol-analysis.md`](network/protocol-analysis.md)

---

## 10. Principais Achados

| ID  | Achado                                          | Risco   |
|-----|-------------------------------------------------|---------|
| F01 | UART exposta — log de boot com dados sensíveis  | Alto    |
| F02 | Flash sem criptografia — firmware extraível     | Alto    |
| F03 | MQTT sem TLS e sem autenticação                 | Alto    |
| F04 | Credenciais Wi-Fi em texto claro no firmware    | Alto    |
| F05 | OTA via HTTP sem verificação de assinatura      | Alto    |
| F06 | JTAG acessível e não desabilitado               | Médio   |
| F07 | Device ID estático e previsível                 | Médio   |
| F08 | Mensagens de debug verbose em produção          | Baixo   |

Tabela completa com evidências: [`findings/findings.md`](findings/findings.md)

---

## 11. Recomendações Principais

1. Habilitar **Flash Encryption** + **Secure Boot v2** antes de qualquer produção.
2. Migrar MQTT para **MQTT sobre TLS (porta 8883)** com autenticação por certificado.
3. Remover ou proteger credenciais Wi-Fi do firmware — usar NVS criptografado ou provisionamento em campo.
4. Desabilitar JTAG e UART em builds de produção via eFuse (`esp_efuse_disable_jtag`, `esp_efuse_disable_uart_download_mode`).
5. Assinar imagens OTA e validar assinatura antes de aplicar atualização.
6. Substituir device ID sequencial por identificador único por dispositivo.
7. Desativar logs de debug (`CONFIG_LOG_DEFAULT_LEVEL_NONE`) em builds de produção.

Plano detalhado: [`remediation/hardening-plan.md`](remediation/hardening-plan.md)

---

## 12. Como Reproduzir os Testes (Ambiente Autorizado)

> Execute **apenas** no dispositivo de laboratório fornecido, em rede isolada.

### Extração do firmware
```bash
# Conectar ESP32 via USB, identificar porta serial
esptool.py --port /dev/ttyUSB0 --baud 921600 read_flash 0x0 0x400000 nexasense_firmware.bin
sha256sum nexasense_firmware.bin
```

### Análise estática
```bash
binwalk nexasense_firmware.bin
strings nexasense_firmware.bin | grep -E "(ssid|password|mqtt|http|192\.168)"
```

### Monitoramento UART
```bash
screen /dev/ttyUSB0 115200
# ou
minicom -D /dev/ttyUSB0 -b 115200
```

### Captura de tráfego MQTT
```bash
# Na máquina de análise na mesma rede de laboratório
tcpdump -i eth0 -w nexasense_mqtt.pcapng port 1883
# Abrir no Wireshark para inspeção do payload
```

---

## 13. Vídeo de Demonstração

> Link: https://youtu.be/l9kXt4JnXpE  
> Plataforma: YouTube (modo não listado)

---

*Avaliação realizada em 30/09/2026 — Ambiente educacional UniFeCAF.*  
*Credenciais ou dados sensíveis encontrados não foram publicados neste repositório.*
