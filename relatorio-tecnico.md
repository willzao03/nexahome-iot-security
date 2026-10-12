# Relatório Técnico de Avaliação de Segurança
## NexaSense — Do Protótipo ao Produto Seguro

---

**Cliente:** NexaHome Technologies  
**Produto avaliado:** NexaSense v0.9.1-prototype  
**Analista:** NexaHome Security Assessment Team  
**Data:** 30 de setembro de 2026  
**Classificação:** Confidencial — Uso Interno  
**Escopo:** Ambiente educacional de laboratório — UniFeCAF  

> Todo o trabalho foi realizado exclusivamente no dispositivo de laboratório fornecido, em rede isolada. Nenhum teste foi realizado contra dispositivos de terceiros, serviços externos ou redes de produção.

---

## Sumário Executivo

O NexaSense é um dispositivo IoT baseado em ESP32 destinado ao monitoramento de temperatura e umidade em ambientes residenciais e comerciais. A avaliação técnica do protótipo identificou **10 achados de segurança**, dos quais **7 são classificados como risco alto** e constituem bloqueadores para qualquer implantação comercial.

O protótipo foi desenvolvido priorizando a funcionalidade, mantendo ativas diversas características de depuração que não devem estar presentes em produtos entregues a clientes. A interface UART expõe credenciais de rede em texto claro durante o boot. O firmware pode ser extraído sem autenticação. A comunicação MQTT ocorre sem criptografia sobre um broker sem controle de acesso. O mecanismo de atualização de firmware não verifica a autenticidade das imagens baixadas.

**Nenhuma dessas condições requer exploração sofisticada.** Todas foram demonstradas com ferramentas acessíveis em ambiente de laboratório controlado.

A boa notícia é que a plataforma ESP32 oferece mecanismos nativos — Flash Encryption, Secure Boot v2, MQTT TLS — que endereçam diretamente todos os riscos críticos identificados. O caminho para a versão comercial segura está bem definido e é tecnicamente viável.

---

## 1. Descrição do Dispositivo Analisado

O NexaSense é um dispositivo de monitoramento ambiental com os seguintes componentes principais:

| Componente | Especificação |
|------------|---------------|
| Microcontrolador | ESP32-WROOM-32D (Xtensa LX6 dual-core, 240 MHz) |
| Memória Flash | W25Q32 — 4 MB SPI Flash externa |
| RAM | 520 KB SRAM interna |
| Sensor | DHT22 (temperatura −40 a +80 °C; umidade 0–100% RH) |
| Conectividade | Wi-Fi 802.11 b/g/n, 2,4 GHz |
| Interfaces físicas | UART0 (USB-Serial CP2102), JTAG (GPIO 12–15), SPI, I²C, USB micro |
| Firmware | ESP-IDF v5.1.2, build educacional |
| Protocolo de rede | MQTT 3.1.1 (porta 1883, sem TLS) |
| Atualização | OTA via HTTP (sem verificação de assinatura) |
| Alimentação | 5 V via USB ou 3,3 V regulado |

O dispositivo coleta leituras de temperatura e umidade a cada 30 segundos e as publica via MQTT em formato JSON para uma plataforma de monitoramento centralizada.

---

## 2. Diagrama Simplificado da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                        NexaSense (ESP32)                           │
│                                                                     │
│  ┌───────────┐   ┌─────────────┐   ┌──────────┐   ┌───────────┐   │
│  │  Firmware │   │  Flash SPI  │   │  UART0   │   │   JTAG    │   │
│  │ ESP-IDF   │   │  W25Q32     │   │ ⚠ Exposta│   │ ⚠ Ativo  │   │
│  │ v5.1.2    │   │  4 MB       │   │ sem prot.│   │ GPIO 12-15│   │
│  └───────────┘   └─────────────┘   └──────────┘   └───────────┘   │
│         │               │                                          │
│         └───────────────┘                                          │
│                 │                                                  │
│          ┌──────────────┐                                          │
│          │  Wi-Fi       │                                          │
│          │ 802.11 b/g/n │                                          │
│          └──────┬───────┘                                          │
└─────────────────┼───────────────────────────────────────────────┘
                  │
           Rede de laboratório (192.168.1.0/24)
                  │
          ┌───────┴────────────────────────────┐
          │                                    │
   ┌──────▼──────────┐              ┌──────────▼──────┐
   │  Broker MQTT    │              │  Servidor OTA   │
   │  Mosquitto      │              │  :8080          │
   │  :1883 ⚠ sem TLS│              │  ⚠ HTTP sem     │
   │  ⚠ anônimo     │              │    assinatura   │
   └─────────────────┘              └─────────────────┘
          │
   ┌──────▼──────────┐
   │  Plataforma de  │
   │  Monitoramento  │
   └─────────────────┘

Sensor DHT22 ──── I²C ────► ESP32
```

**Diagrama visual completo:** `architecture/architecture-diagram.svg`

---

## 3. Identificação dos Principais Componentes

### Hardware
- **MCU:** ESP32-WROOM-32D com Wi-Fi, Bluetooth e criptografia por hardware (AES, SHA, RSA — não utilizados no protótipo)
- **Flash SPI:** W25Q32JV — chip de 4 MB externo à CPU, soldado na placa, acessível via barramento SPI
- **USB-Serial:** CP2102 (Silicon Labs) — bridge entre UART0 do ESP32 e USB, habilitando o log de depuração

### Firmware
- **Framework:** ESP-IDF v5.1.2 (IoT Development Framework da Espressif)
- **Partições:** bootloader, partition table, NVS, app factory, ota_0, ota_data
- **Bibliotecas:** mqtt_client, wifi_provisioning, nvs_flash, esp_http_client, driver/dht

### Rede
- **Protocolo de mensageria:** MQTT 3.1.1
- **Broker:** Mosquitto (open source)
- **Topologia de tópicos:** `/nexasense/{device_id}/telemetry` (publish) e `/nexasense/{device_id}/cmd` (subscribe)

---

## 4. Mapa da Superfície de Ataque

```
SUPERFÍCIE FÍSICA
├── UART0 — acesso ao log de boot com credenciais
├── UART0 — modo download para reflash do firmware
├── JTAG (GPIO 12–15) — depuração e dump de memória RAM
├── SPI Flash — dump direto do chip via programador externo
└── USB — reflash sem autenticação (sem Secure Boot)

SUPERFÍCIE DE FIRMWARE
├── Credenciais Wi-Fi hardcoded no binário
├── Credenciais MQTT hardcoded no binário
├── NVS não criptografada (credenciais acessíveis)
├── Mensagens de debug com dados sensíveis
└── Identificadores de desenvolvimento expostos

SUPERFÍCIE DE REDE / COMUNICAÇÃO
├── MQTT sem TLS (texto claro na rede)
├── Broker sem autenticação e sem ACL
├── Payload de telemetria sem criptografia ou assinatura
├── OTA via HTTP sem verificação de integridade
└── Device ID estático e enumerável
```

---

## 5. Metodologia Utilizada

A avaliação seguiu a estrutura do **OWASP IoT Security Testing Guide (ISTG)**, adaptada ao ambiente educacional de laboratório, com 8 etapas sequenciais:

| Etapa | Descrição | Ferramentas |
|-------|-----------|-------------|
| 1 | Reconhecimento do dispositivo | Inspeção visual, datasheets |
| 2 | Preservação e identificação do firmware | esptool.py, sha256sum |
| 3 | Análise estática do firmware | binwalk, strings |
| 4 | Análise das interfaces físicas | screen, minicom |
| 5 | Análise das comunicações de rede | Wireshark, tcpdump |
| 6 | Demonstração controlada de fragilidades | mosquitto_pub, mosquitto_sub |
| 7 | Mapeamento e classificação de riscos | Matriz Impacto × Probabilidade |
| 8 | Proposta de hardening | ESP-IDF Security Docs, ETSI EN 303 645 |

---

## 6. Análise do Firmware

### 6.1 Preservação e Integridade

Antes de qualquer análise, a imagem original foi extraída e preservada:

```bash
esptool.py --port /dev/ttyUSB0 --baud 921600 read_flash 0x0 0x400000 nexasense_firmware_original.bin
```

| Campo | Valor |
|-------|-------|
| Arquivo | nexasense_firmware_original.bin |
| Tamanho | 4.194.304 bytes (4 MB) |
| SHA-256 | `a3f8c1d2e94b57062f1a8390dc4e27b5f6083c91ad254e78b1f9302e6c7d4158` |
| Data | 2026-09-30 |

A cópia de trabalho possui hash idêntico, confirmando integridade.

### 6.2 Estrutura identificada (binwalk)

```
0x000000  Bootloader ESP-IDF
0x008000  Partition Table
0x009000  NVS (Non-Volatile Storage) — não criptografada
0x010000  Aplicação principal (ESP-IDF App Image)
0x130000  Partição OTA
```

A ausência de Flash Encryption é imediatamente evidenciada pelo fato de `binwalk` identificar todas as estruturas sem nenhum processo de decriptação.

### 6.3 Informações sensíveis encontradas via strings

| String encontrada | Tipo | Risco |
|-------------------|------|-------|
| `NEXAHOME_WIFI_SSID=[REDACTED]` | Credencial hardcoded | Alto |
| `NEXAHOME_WIFI_PASS=[REDACTED]` | Credencial hardcoded | Alto |
| `mqtt://192.168.1.10:1883` | Endpoint sem TLS | Alto |
| `mqtt_user/mqtt_pass=[REDACTED]` | Credencial MQTT | Alto |
| `http://192.168.1.10:8080/firmware/` | OTA via HTTP | Alto |
| `[NVS] ssid=%s password=%s` | Log imprime credenciais | Médio |
| `device_id=device001` | ID estático | Médio |
| `fw_version=0.9.1-prototype` | Versão de desenvolvimento | Baixo |

### 6.4 Mecanismo OTA analisado

O firmware implementa OTA via `esp_https_ota` configurado sem certificado CA e sem TLS (`http://` em vez de `https://`). Não há verificação de assinatura RSA/ECDSA da imagem baixada. Um atacante posicionado na mesma rede pode substituir a imagem por firmware malicioso sem que o dispositivo detecte a adulteração.

---

## 7. Análise das Interfaces Físicas

### 7.1 UART0 — Risco Alto

A interface UART0 está ativa e acessível via conector USB sem qualquer proteção. Durante o boot, o firmware imprime um log completo que inclui credenciais Wi-Fi, IP e credenciais do broker MQTT.

**Evidência coletada:**
```
[WIFI] Connecting to SSID: NexaHome_Lab
[NVS] ssid=NexaHome_Lab password=[REDACTED — visível no dispositivo]
[MQTT] Connecting to broker: mqtt://192.168.1.10:1883
[MQTT] Client ID: device001
```

Um atacante com acesso físico por menos de 30 segundos (reset + leitura do log) obtém todas as credenciais necessárias para acessar a rede Wi-Fi do cliente e o broker MQTT da instalação.

Além do log, a UART permite regravação completa do firmware quando o pino BOOT (GPIO 0) é mantido em nível baixo durante o reset — sem qualquer autenticação, pois o Secure Boot não está habilitado.

### 7.2 JTAG — Risco Médio

Os pinos JTAG (GPIO 12, 13, 14, 15) estão fisicamente acessíveis na placa e o eFuse `JTAG_DISABLE` não foi programado. Com um adaptador FTDI (~R$50) e OpenOCD, é possível conectar ao core do ESP32 em modo de depuração, pausar a execução, inspecionar registradores e fazer dump da memória RAM — potencialmente expondo credenciais carregadas da NVS em tempo de execução.

### 7.3 Flash SPI — Risco Médio

O chip W25Q32 está acessível na placa. Sem Flash Encryption, um atacante pode usar um programador SPI com clip SOIC8 para extrair o conteúdo completo da flash sem passar pela CPU — bypass total de qualquer proteção de software.

### 7.4 Interface USB / Boot Mode — Risco Médio

O conector micro-USB combinado com o botão BOOT permite reflash completo do firmware. Sem Secure Boot, qualquer imagem pode ser instalada sem verificação de autenticidade.

---

## 8. Análise das Comunicações

### 8.1 Protocolo e configuração

O NexaSense utiliza **MQTT 3.1.1 sobre TCP na porta 1883** (plaintext). O broker Mosquitto está configurado com `allow_anonymous true`, sem ACL e sem TLS.

### 8.2 Autenticação, Confidencialidade e Integridade

| Propriedade | Status | Observação |
|-------------|--------|------------|
| Criptografia de transporte | ❌ Ausente | Porta 1883 plaintext; porta 8883 não utilizada |
| Autenticação do cliente | ❌ Ausente | Broker aceita conexões anônimas |
| Controle de acesso (ACL) | ❌ Ausente | Qualquer cliente assina/publica qualquer tópico |
| Autenticação de mensagens | ❌ Ausente | Sem HMAC ou assinatura no payload |
| Proteção contra replay | ❌ Ausente | Mensagens podem ser capturadas e reenviadas |

### 8.3 Payload capturado (Wireshark)

```json
{
  "device_id": "device001",
  "temp": 24.5,
  "hum": 62.3,
  "ts": 1727737200
}
```

Todo o conteúdo é transmitido em texto claro. O pacote MQTT CONNECT expõe username e password em texto claro na rede.

### 8.4 Demonstração: injeção de comando via MQTT

Qualquer cliente na rede de laboratório conseguiu publicar comandos ao dispositivo sem autenticação:

```bash
mosquitto_pub -h 192.168.1.10 -p 1883 \
  -t "/nexasense/device001/cmd" \
  -m '{"cmd":"reboot","source":"attacker"}'
# → Broker aceitou; dispositivo executou o reinício
```

Esta demonstração evidencia que, em uma instalação real, um atacante na mesma rede Wi-Fi poderia reinicializar, reconfigurar ou potencialmente comprometer todos os dispositivos NexaSense da instalação.

---

## 9. Riscos Identificados e Classificação

### Tabela de Achados

| Achado | Evidência | Impacto | Probabilidade | Risco | Recomendação |
|--------|-----------|---------|---------------|-------|--------------|
| **F01** UART com log de credenciais | Log boot via `screen /dev/ttyUSB0` mostra SSID e senha Wi-Fi em texto claro | Alto | Alta | **Alto** | Desabilitar logs em produção; nunca logar credenciais |
| **F02** Flash sem criptografia | `binwalk` analisa estrutura completa sem decriptação; `esptool.py` extrai firmware livre | Alto | Alta | **Alto** | Habilitar Flash Encryption (AES-256) via eFuse |
| **F03** MQTT sem TLS | Wireshark captura payload completo em texto claro na porta 1883 | Alto | Alta | **Alto** | Migrar para MQTTS porta 8883 com TLS 1.3 |
| **F04** Credenciais Wi-Fi hardcoded | `strings` revela `NEXAHOME_WIFI_SSID` e `WIFI_PASS` no binário | Alto | Alta | **Alto** | Provisionamento BLE em campo; NVS criptografada |
| **F05** OTA via HTTP sem assinatura | Requisição `GET http://` capturada; sem certificado CA nem verificação ECDSA | Alto | Média | **Alto** | HTTPS OTA + Secure Boot v2 com assinatura RSA-3072 |
| **F06** Broker MQTT sem autenticação | `mosquitto_pub` publica sem credenciais; comando executado pelo dispositivo | Alto | Alta | **Alto** | `allow_anonymous false`; TLS mútuo; ACL por dispositivo |
| **F07** JTAG habilitado e acessível | GPIO 12–15 acessíveis; eFuse `JTAG_DISABLE` não programado | Alto | Média | **Médio** | `esp_efuse_disable_jtag()` em builds de produção |
| **F08** Device ID estático (`device001`) | `device_id` idêntico no firmware, NVS e payload MQTT | Médio | Alta | **Médio** | UUID baseado em MAC address único por dispositivo |
| **F09** NVS não criptografada | `nvs_partition_parser` lê chaves `wifi/password` e `mqtt/password` diretamente | Alto | Alta | **Alto** | `nvs_flash_secure_init()` com NVS Encryption |
| **F10** Versão "prototype" exposta | String `fw_version=0.9.1-prototype` no binário, UART e payload MQTT | Baixo | Alta | **Médio** | Remover identificadores de desenvolvimento de builds finais |

### Distribuição de riscos

```
Alto   ████████████████████████████  7 achados (70%)
Médio  ████████████                  3 achados (30%)
Baixo  ░░░░                          0 achados
```

---

## 10. Relação dos Achados com Referências de Segurança

### OWASP IoT Security Testing Guide (ISTG)

| Achado | Caso de teste OWASP ISTG |
|--------|--------------------------|
| F01, F10 | IOT-FW-INFO-001: Identificação de informações sensíveis expostas |
| F02 | IOT-FW-002: Proteção de firmware armazenado |
| F03, F06 | IOT-COM-CRYPT-001: Criptografia de comunicações |
| F05 | IOT-FW-UPD-001: Autenticação de atualizações |
| F07 | IOT-HW-DEBUG-001: Interfaces de depuração expostas |

O OWASP ISTG foi utilizado para **estruturar as etapas da avaliação** e para mapear os achados a casos de teste reconhecidos, fornecendo vocabulário comum para comunicar os riscos identificados.

### NIST IR 8259A — IoT Device Cybersecurity Capability Core Baseline

O NIST IR 8259A define capacidades mínimas que dispositivos IoT deveriam possuir. A comparação com o protótipo NexaSense revela lacunas significativas:

| Capacidade NIST | Status no NexaSense |
|-----------------|---------------------|
| Identificação do dispositivo (única por dispositivo) | ❌ Device ID estático |
| Configuração (sem credenciais padrão/hardcoded) | ❌ Credenciais hardcoded |
| Proteção de dados (criptografia em repouso) | ❌ Flash e NVS sem criptografia |
| Controle de acesso às interfaces | ❌ UART, JTAG, MQTT sem controle |
| Atualização de software (autenticada) | ❌ OTA sem verificação |
| Consciência do estado de segurança | ❌ Sem telemetria de segurança |

### ETSI EN 303 645 v3.1.3 — Cyber Security for Consumer IoT

A ETSI EN 303 645 é a principal norma de segurança para produtos IoT de consumo na União Europeia e referência global. Os achados F04 e F09 violam diretamente o requisito **§5.1** (*No universal default passwords* — sem senhas padrão universais ou hardcoded). Os achados F03 e F06 violam **§5.8** (*Ensure that personal data is secure* — dados transmitidos devem ser protegidos). O achado F05 viola **§5.3** (*Keep software updated — secure update mechanism*).

### MITRE EMB3D — Embedded Device Threat Model

O MITRE EMB3D cataloga ameaças específicas para dispositivos embarcados. Os achados se relacionam diretamente com:

| Ameaça EMB3D | Achados relacionados |
|--------------|---------------------|
| TEM-0003: Firmware Extraction via Hardware Interface | F01, F02 |
| TEM-0009: Exposed Privileged Debug Interfaces | F07 |
| TEM-0012: Firmware Update without Integrity Verification | F05 |
| TEM-0021: Cleartext Transmission of Sensitive Data | F03, F04 |

### Espressif ESP-IDF Security Documentation

A documentação da Espressif confirma que o ESP32 possui todos os mecanismos necessários para endereçar os riscos críticos identificados. **Secure Boot e Flash Encryption possuem funções complementares** na proteção do software armazenado — Flash Encryption protege o conteúdo em repouso enquanto Secure Boot garante que apenas firmware autêntico é executado. Esses mecanismos não foram ativados no protótipo.

---

## 11. Recomendações de Mitigação

### Prioridade Crítica — Bloqueadores para implantação comercial

1. **Habilitar Flash Encryption (AES-256)** — impede extração legível do firmware e da NVS via UART ou SPI.
2. **Habilitar Secure Boot v2 (RSA-3072)** — garante que apenas firmware assinado pela NexaHome pode ser executado.
3. **Migrar MQTT para TLS 1.3 (porta 8883) com autenticação por certificado por dispositivo** — elimina interceptação e injeção de mensagens.
4. **Remover credenciais hardcoded; implementar provisionamento BLE em campo** — cada dispositivo recebe credenciais únicas no momento da instalação.
5. **OTA via HTTPS com verificação de assinatura ECDSA** — impede instalação de firmware malicioso via MitM.
6. **Habilitar NVS Encryption** — protege credenciais armazenadas mesmo se a flash for extraída.
7. **Configurar broker com ACL por dispositivo e TLS mútuo obrigatório** — cada dispositivo só pode acessar seus próprios tópicos.

### Prioridade Alta — Implementar antes do lançamento

8. **Desabilitar JTAG via eFuse** (`esp_efuse_disable_jtag()`) — impede depuração não autorizada em campo.
9. **Desabilitar UART download mode via eFuse** — impede reflash via acesso físico.
10. **Definir `CONFIG_LOG_DEFAULT_LEVEL_NONE`** em builds de produção — elimina exposição de informações operacionais.

### Prioridade Média — Melhorias para versões subsequentes

11. **Gerar device ID único por dispositivo** baseado em MAC address ou certificado — elimina enumeração.
12. **Implementar proteção física da placa** — remoção de headers de debug, potting com resina epóxi, enclosure com lacre de violação.
13. **Estabelecer política de divulgação responsável** e processo de resposta a incidentes para o produto.

---

## 12. Proposta de Hardening para Versão Comercial

A tabela abaixo apresenta o estado de segurança antes e depois da aplicação do plano de hardening completo:

| Aspecto | Protótipo (atual) | Versão Comercial (proposta) |
|---------|-------------------|------------------------------|
| Firmware em repouso | Texto claro — extraível | AES-256 via Flash Encryption |
| Autenticidade do firmware | Sem verificação | RSA-3072 via Secure Boot v2 |
| Comunicação MQTT | TCP porta 1883 plaintext | TLS 1.3 porta 8883 + cert |
| Autenticação no broker | Anônima | TLS mútuo + ACL por dispositivo |
| Credenciais Wi-Fi | Hardcoded no binário | Provisionamento BLE em campo |
| Atualização de firmware | HTTP sem assinatura | HTTPS + ECDSA verificado |
| Interface UART | Log completo com credenciais | Desabilitada via eFuse |
| Interface JTAG | Ativa, pinos acessíveis | Desabilitada via eFuse |
| NVS | Texto claro | NVS Encryption habilitada |
| Device ID | Estático `device001` | UUID único baseado em MAC |
| Logs em produção | Verbose com dados sensíveis | Desabilitados completamente |

---

## 13. Exemplo Real Pesquisado — Lição para a NexaHome

### Caso: Vulnerabilidades no Firmware TP-Link Archer C5

Pesquisadores da IOACTIVE e do projeto OWASP IoT documentaram publicamente vulnerabilidades no firmware de roteadores TP-Link Archer C5 amplamente distribuídos, incluindo:

- **Credenciais hardcoded** no binário do firmware (senha de serviço técnico oculta), descobertas via extração pelo barramento UART — a mesma interface presente e vulnerável no NexaSense.
- **Interface telnet habilitada por padrão** sem autenticação — equivalente ao broker MQTT do NexaSense configurado com `allow_anonymous true`.
- **Atualização de firmware sem verificação de assinatura** — idêntico ao mecanismo OTA via HTTP do NexaSense.

O caso TP-Link demonstrou que estas não são vulnerabilidades teóricas: dispositivos com características similares foram explorados em escala, com atacantes obtendo controle administrativo completo de roteadores instalados em residências e empresas globalmente. A origem do problema foi exatamente a mesma da NexaHome: um produto que evoluiu de protótipo para lançamento sem revisão sistemática de segurança.

**Lição para a NexaHome:** A transição do protótipo NexaSense para o produto comercial exige uma revisão explícita e documentada de segurança, desabilitando sistematicamente todas as funcionalidades habilitadas por conveniência durante o desenvolvimento. Um único dispositivo comprometido em campo pode expor as credenciais Wi-Fi do cliente e fornecer acesso à rede interna da instalação.

**Fonte:** IOACTIVE Security Research — TP-Link Archer; CVE-2021-41450; OWASP IoT Attack Surface Areas Project.

---

## 14. Conclusão

O NexaSense em seu estado atual de protótipo **não está apto para implantação comercial**. Os 7 achados de risco alto identificados representam condições exploráveis com ferramentas e conhecimento acessíveis — não requerem adversários sofisticados.

A avaliação demonstra uma metodologia estruturada que mapeia evidências técnicas concretas a riscos classificados e a recomendações de mitigação baseadas em normas reconhecidas. O ESP32 oferece todos os mecanismos necessários para endereçar os riscos críticos. O que falta é a decisão de ativá-los antes do lançamento.

O plano de hardening proposto, quando implementado na íntegra, transforma o NexaSense de um protótipo com múltiplos vetores de ataque triviais em um produto com postura de segurança adequada para o ambiente residencial e comercial a que se destina.

---

## Referências

1. OWASP Foundation. *IoT Security Testing Guide (ISTG)*. Disponível em: https://owasp.org/www-project-iot-security-testing-guide/
2. NIST. *IR 8259A — IoT Device Cybersecurity Capability Core Baseline*. 2020. Disponível em: https://nvlpubs.nist.gov/nistpubs/ir/2020/NIST.IR.8259A.pdf
3. ETSI. *EN 303 645 v3.1.3 — Cyber Security for Consumer Internet of Things*. Setembro 2024.
4. MITRE. *EMB3D — Embedded Device Threat Model*. Disponível em: https://emb3d.mitre.org/
5. Espressif Systems. *ESP-IDF Security Features Documentation*. Disponível em: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/security/index.html
6. IOACTIVE. *TP-Link Security Research*. Disponível em: https://ioactive.com/tp-link-security-research/
7. NVD. *CVE-2021-41450*. Disponível em: https://nvd.nist.gov/vuln/detail/CVE-2021-41450

---

*Relatório gerado em 30 de setembro de 2026.*  
*Credenciais e dados sensíveis identificados durante a avaliação foram redatados neste documento.*  
*Vídeo de demonstração: consultar link no README.md do repositório.*
