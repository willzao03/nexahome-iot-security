# Mapeamento de Interfaces Físicas — NexaSense ESP32

**Data:** 2026-09-30  
**Analista:** NexaHome Security Assessment Team  
**Dispositivo:** NexaSense v0.9 (ESP32-WROOM-32D)  
**Metodologia:** Inspeção visual, leitura de datasheets, monitoramento de saída UART

---

## Visão Geral das Interfaces Identificadas

| Interface | Localização na Placa     | Estado no Protótipo      | Risco (sem proteção) |
|-----------|--------------------------|--------------------------|----------------------|
| UART0     | Conector USB-B / pinos TX/RX expostos | Ativo, sem proteção | Alto |
| JTAG      | GPIO 12, 13, 14, 15 (pinos de teste) | Habilitado, pinos acessíveis | Médio–Alto |
| SPI       | GPIO 18 (CLK), 19 (MISO), 23 (MOSI), 5 (CS) | Conectado ao flash W25Q32 | Médio |
| I²C       | GPIO 21 (SDA), 22 (SCL) | Conectado ao DHT22 | Baixo |
| USB (programação) | Conector micro-USB | Sem boot lock | Médio |
| Pinos de alimentação | 3V3, GND, 5V (headers expostos) | Acessíveis | Baixo |

---

## Interface 1 — UART0 (Universal Asynchronous Receiver-Transmitter)

### Identificação
- **Pinos:** TX0 (GPIO 1), RX0 (GPIO 3)
- **Velocidade padrão:** 115200 baud
- **Chip USB-Serial:** CP2102 (Silicon Labs)
- **Conector:** Micro-USB direto ao CP2102

### O que essa interface permite fazer
A UART0 é a interface serial principal do ESP32. No protótipo NexaSense ela está configurada para:
1. **Saída de log de boot completo** — o ESP-IDF imprime todas as etapas de inicialização.
2. **Download de firmware** — o ESP32 pode ter firmware regravado via UART quando o pino BOOT (GPIO 0) é mantido em nível baixo durante o reset.
3. **Console interativo** — o firmware educacional mantém o monitor serial ativo em produção.

### Evidência — Saída UART capturada durante boot

```
rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
configsip: 0, SPIWP:0xee
clk_drv:0x00,q_drv:0x00,d_drv:0x00,cs0_drv:0x00,hd_drv:0x00,wp_drv:0x00
mode:DIO, clock div:2
load:0x3fff0030,len:7176
...
I (342) boot: Loaded app from partition at offset 0x10000
I (342) boot: Disabling RNG early entropy source...
I (362) cpu_start: Starting scheduler on PRO CPU.

[BOOT] Starting NexaSense firmware v0.9.1-prototype
[WIFI] Connecting to SSID: NexaHome_Lab
[WIFI] Password: [REDACTED - visível na UART sem redação no firmware real]
[WIFI] Connected! IP: 192.168.1.42
[MQTT] Connecting to broker: mqtt://192.168.1.10:1883
[MQTT] Client ID: device001
[NVS] ssid=NexaHome_Lab password=[REDACTED]
[MQTT] Connected to broker
[SENSOR] Temp=24.5 Hum=62.3
[MQTT] Publishing: /nexasense/device001/telemetry -> {"device_id":"device001","temp":24.5,"hum":62.3,"ts":1727737200}
```

### Análise de Risco

| Aspecto             | Avaliação                                                                                 |
|---------------------|-------------------------------------------------------------------------------------------|
| **Fragilidade**     | UART ativa com log verbose, incluindo credenciais Wi-Fi e MQTT visíveis em texto claro    |
| **Ameaça**          | Atacante com acesso físico ao dispositivo conecta cabo USB e lê toda a saída serial       |
| **Impacto**         | Obtenção de SSID+senha Wi-Fi, credenciais MQTT, IP do broker, device ID, versão de firmware |
| **Probabilidade**   | Alta — qualquer pessoa com acesso físico ao dispositivo instalado pode fazer isso         |
| **Risco**           | **Alto**                                                                                  |
| **Proteções atuais**| Nenhuma                                                                                   |

### Mitigação Proposta
- Desabilitar saída de log em builds de produção: `CONFIG_LOG_DEFAULT_LEVEL_NONE`
- Desabilitar UART download mode via eFuse: `esp_efuse_disable_uart_download_mode()`
- Nunca imprimir credenciais nos logs, independentemente do nível de log
- Aplicar resina epóxi sobre os pinos físicos em produtos comerciais

---

## Interface 2 — JTAG (Joint Test Action Group)

### Identificação
- **Pinos:** TDI (GPIO 12), TCK (GPIO 13), TMS (GPIO 14), TDO (GPIO 15)
- **Protocolo:** IEEE 1149.1
- **Estado:** Habilitado (padrão de fábrica no ESP32)
- **Localização:** Pinos de teste acessíveis na borda da placa de desenvolvimento

### O que essa interface permite fazer
O JTAG permite:
1. **Acesso ao modo de depuração em tempo real** (breakpoints, leitura de registradores, inspeção de memória RAM).
2. **Dump completo da memória interna** (IRAM, DRAM, registradores).
3. **Bypass de algumas proteções de software** se o Flash Encryption não estiver habilitado.
4. Com ferramentas como OpenOCD + GDB, é possível pausar a execução do firmware e inspecionar variáveis em memória, incluindo credenciais carregadas da NVS.

### Análise de Risco

| Aspecto             | Avaliação                                                                                 |
|---------------------|-------------------------------------------------------------------------------------------|
| **Fragilidade**     | Pinos JTAG acessíveis fisicamente; interface não desabilitada via eFuse                   |
| **Ameaça**          | Atacante com acesso físico conecta adaptador JTAG (FTDI) e usa OpenOCD para depuração     |
| **Impacto**         | Leitura de memória RAM em execução, dump de credenciais carregadas, bypass de lógica      |
| **Probabilidade**   | Média — requer equipamento específico (adaptador JTAG ~$10) e conhecimento técnico        |
| **Risco**           | **Médio–Alto**                                                                            |
| **Proteções atuais**| Nenhuma (eFuse `JTAG_DISABLE` não programado)                                             |

### Mitigação Proposta
- Desabilitar JTAG permanentemente via eFuse em produção: `esp_efuse_disable_jtag()`
- Documentar que esta é uma ação **irreversível** — não realizar durante testes educacionais
- Cobrir pinos fisicamente com resina ou soldar componentes sobre os pads

---

## Interface 3 — SPI (Serial Peripheral Interface) — Flash

### Identificação
- **Pinos:** CLK (GPIO 18), MISO (GPIO 19), MOSI (GPIO 23), CS (GPIO 5)
- **Dispositivo conectado:** W25Q32JV (Winbond) — Flash SPI 4 MB
- **Modo:** DIO (Dual I/O) a 80 MHz
- **Chip físico:** Componente SMD 8-pinos acessível na placa

### O que essa interface permite fazer
O barramento SPI conecta o ESP32 à memória flash externa. Sem Flash Encryption:
1. Um atacante pode soldar fios nos pads do chip W25Q32 e usar um programador SPI (ex.: Bus Pirate, CH341A) para fazer dump completo da flash sem passar pela CPU.
2. O conteúdo extraído é idêntico ao obtido via `esptool.py` — firmware, NVS com credenciais, configurações.

### Análise de Risco

| Aspecto             | Avaliação                                                                                    |
|---------------------|----------------------------------------------------------------------------------------------|
| **Fragilidade**     | Flash sem criptografia; chip SPI acessível fisicamente                                       |
| **Ameaça**          | Dump direto da flash com programador SPI (contorna qualquer proteção de software)            |
| **Impacto**         | Extração completa do firmware e de todos os dados armazenados (credenciais, configurações)   |
| **Probabilidade**   | Baixa–Média — requer dessoldagem ou uso de clip SOIC; habilidade técnica necessária          |
| **Risco**           | **Médio**                                                                                    |
| **Proteções atuais**| Nenhuma                                                                                      |

### Mitigação Proposta
- Habilitar **Flash Encryption** no ESP32 (AES-256 via eFuse `FLASH_CRYPT_CNT`)
- Com Flash Encryption, o conteúdo extraído via SPI é ilegível sem a chave armazenada internamente no ESP32

---

## Interface 4 — I²C (Inter-Integrated Circuit) — Sensores

### Identificação
- **Pinos:** SDA (GPIO 21), SCL (GPIO 22)
- **Dispositivo conectado:** DHT22 (sensor de temperatura e umidade)
- **Velocidade:** 100 kHz (Standard Mode)

### O que essa interface permite fazer
- Leitura e potencialmente escrita em sensores conectados.
- No NexaSense, apenas o DHT22 está no barramento — risco limitado ao contexto atual.
- Em versões futuras com mais sensores, um atacante com acesso físico poderia injetar leituras falsas para manipular alertas no sistema de monitoramento.

### Análise de Risco

| Aspecto             | Avaliação                                                   |
|---------------------|-------------------------------------------------------------|
| **Fragilidade**     | Barramento I²C acessível em pinos de teste                  |
| **Ameaça**          | Injeção de dados falsos de sensor                           |
| **Impacto**         | Dados de monitoramento incorretos; alarmes falsos/suprimidos|
| **Probabilidade**   | Baixa — requer acesso físico e conhecimento do protocolo    |
| **Risco**           | **Baixo**                                                   |
| **Proteções atuais**| Nenhuma (sem autenticação no barramento I²C)                |

---

## Interface 5 — USB / Boot Mode (Programação)

### Identificação
- **Conector:** Micro-USB
- **Função:** Programação via esptool.py e comunicação serial
- **Boot mode:** Determinado pelo nível em GPIO 0 no momento do reset
  - GPIO 0 = LOW → modo download (firmware pode ser regravado)
  - GPIO 0 = HIGH → boot normal

### O que essa interface permite fazer
- Com acesso físico ao conector USB e ao botão BOOT, qualquer pessoa pode apagar e regravar o firmware completo.
- Sem Secure Boot, não há verificação de que o firmware instalado é autêntico.

### Análise de Risco

| Aspecto             | Avaliação                                                                          |
|---------------------|------------------------------------------------------------------------------------|
| **Fragilidade**     | Firmware pode ser substituído via USB sem autenticação                              |
| **Ameaça**          | Instalação de firmware malicioso por atacante com acesso físico breve               |
| **Impacto**         | Comprometimento completo do dispositivo; possível uso como ponto de pivô na rede    |
| **Probabilidade**   | Média — requer acesso físico ao conector USB                                        |
| **Risco**           | **Médio–Alto**                                                                      |
| **Proteções atuais**| Nenhuma                                                                             |

### Mitigação Proposta
- Habilitar **Secure Boot v2** — impede boot de firmware não assinado
- Desabilitar UART download mode via eFuse após provisionamento de produção

---

## Resumo — Mapa de Superfície de Ataque Físico

```
┌─────────────────────────────────────────────────────────────────┐
│                    NexaSense — Superfície Física                │
├──────────────┬──────────────────────────┬────────────┬──────────┤
│ Interface    │ Vetor de Ataque          │ Impacto    │ Risco    │
├──────────────┼──────────────────────────┼────────────┼──────────┤
│ UART0        │ Log com credenciais      │ Alto       │ Alto     │
│ UART0        │ Reflash via modo download│ Alto       │ Alto     │
│ JTAG         │ Debug / dump de RAM      │ Alto       │ Médio    │
│ SPI (Flash)  │ Dump direto via clip     │ Alto       │ Médio    │
│ USB          │ Reflash sem autenticação │ Alto       │ Médio    │
│ I²C          │ Injeção de dados sensor  │ Médio      │ Baixo    │
└──────────────┴──────────────────────────┴────────────┴──────────┘
```

---

## Demonstração Controlada — UART Boot Log com Credenciais

**Objetivo:** Evidenciar que a interface UART expõe informações sensíveis sem qualquer autenticação.

**Procedimento:**
```bash
# 1. Conectar cabo USB ao dispositivo NexaSense de laboratório
# 2. Abrir monitor serial
screen /dev/ttyUSB0 115200
# ou no Windows:
# PuTTY → Serial → COM3 → 115200 baud

# 3. Pressionar o botão RESET no dispositivo
# 4. Observar a saída — credenciais visíveis imediatamente
```

**Resultado esperado:** O log de boot completo é exibido, incluindo SSID Wi-Fi, IP do broker MQTT e client ID — sem qualquer autenticação necessária para acessar essas informações.

**Evidência:** Captura de tela em `evidence/uart-boot-log.png`  
**Impacto demonstrado:** Atacante com acesso físico por menos de 30 segundos obtém credenciais de rede e infraestrutura MQTT.
