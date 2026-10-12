# Mapeamento de Riscos — NexaSense v0.9

**Data:** 2026-09-30  
**Analista:** NexaHome Security Assessment Team  
**Metodologia de classificação:** Impacto × Probabilidade (OWASP IoT Security Testing Guide)  
**Referências:** OWASP ISTG, NIST IR 8259A, ETSI EN 303 645, MITRE EMB3D, Espressif ESP-IDF Security Docs

---

## Matriz de Risco

```
         PROBABILIDADE
         Baixa    Média    Alta
       ┌────────┬────────┬────────┐
Alto   │ Médio  │  Alto  │  Alto  │
       ├────────┼────────┼────────┤
Médio  │ Baixo  │ Médio  │  Alto  │
       ├────────┼────────┼────────┤
Baixo  │ Baixo  │ Baixo  │ Médio  │
       └────────┴────────┴────────┘
IMPACTO
```

---

## Tabela de Achados

| Achado | Evidência | Superfície | Impacto | Probabilidade | Risco | Referência | Recomendação |
|--------|-----------|------------|---------|---------------|-------|------------|--------------|
| **F01** — UART exposta com log verbose contendo credenciais | Log de boot capturado via `screen /dev/ttyUSB0 115200` mostra SSID, senha Wi-Fi, IP do broker e client ID MQTT em texto claro | Física / Hardware | Alto | Alta | **Alto** | OWASP ISTG IOT-FW-INFO-001; ETSI EN 303 645 §5.4 | Desabilitar logs em produção (`CONFIG_LOG_DEFAULT_LEVEL_NONE`); nunca imprimir credenciais em logs |
| **F02** — Flash sem criptografia — firmware extraível via UART | `esptool.py read_flash` extrai imagem completa de 4 MB sem autenticação; `binwalk` analisa estrutura sem decriptação | Física / Firmware | Alto | Alta | **Alto** | MITRE EMB3D TEM-0003 (Firmware Extraction via Hardware Interface); NIST IR 8259A §3.1 | Habilitar Flash Encryption (AES-256) via eFuse antes da produção |
| **F03** — MQTT sem TLS (porta 1883 plaintext) | Captura Wireshark mostra todo o tráfego legível; porta 8883 (MQTTS) não utilizada | Rede | Alto | Alta | **Alto** | OWASP ISTG IOT-COM-CRYPT-001; ETSI EN 303 645 §5.8 | Migrar para MQTT sobre TLS 1.3 na porta 8883 com certificado por dispositivo |
| **F04** — Credenciais Wi-Fi hardcoded no firmware | `strings` no binário revela `NEXAHOME_WIFI_SSID` e `NEXAHOME_WIFI_PASS`; também presentes na NVS sem criptografia | Firmware | Alto | Alta | **Alto** | ETSI EN 303 645 §5.1 (sem senhas padrão / hardcoded); NIST IR 8259A §3.2 | Usar NVS criptografada ou provisionamento em campo; nunca compilar credenciais no binário |
| **F05** — OTA via HTTP sem verificação de assinatura | Requisição `GET http://192.168.1.10:8080/firmware/...` observada na captura; sem certificado TLS, sem validação RSA/ECDSA do binário | Rede / Firmware | Alto | Média | **Alto** | OWASP ISTG IOT-FW-UPD-001; ETSI EN 303 645 §5.3 | Implementar HTTPS OTA com verificação de assinatura de firmware (ESP-IDF `esp_https_ota` com `verify_peer = true`) |
| **F06** — Broker MQTT sem autenticação (allow_anonymous true) | `mosquitto_pub` consegue publicar no tópico `/nexasense/device001/cmd` sem credenciais; `mosquitto_sub` recebe toda a telemetria | Rede | Alto | Alta | **Alto** | OWASP ISTG IOT-COM-AUTH-001; NIST IR 8259A §3.3 | Configurar ACL no broker; desabilitar `allow_anonymous`; exigir TLS mútuo |
| **F07** — JTAG habilitado com pinos fisicamente acessíveis | GPIO 12-15 acessíveis na placa; eFuse `JTAG_DISABLE` não programado; OpenOCD consegue conectar | Física / Hardware | Alto | Média | **Médio** | MITRE EMB3D TEM-0009 (Exposed Debug Interface); OWASP ISTG IOT-HW-DEBUG-001 | Desabilitar JTAG via eFuse (`esp_efuse_disable_jtag()`) em produção; cobrir pinos fisicamente |
| **F08** — Device ID estático e enumerável (`device001`) | `device_id` fixo no firmware, na NVS e no Client ID MQTT; permite enumeração de dispositivos e subscriptions não autorizadas | Firmware / Rede | Médio | Alta | **Médio** | ETSI EN 303 645 §5.1; NIST IR 8259A §3.1 | Gerar identificador único por dispositivo em produção (MAC-based UUID ou certificado por dispositivo) |
| **F09** — NVS não criptografada com credenciais acessíveis | `nvs_partition_parser` lê chaves `wifi/ssid`, `wifi/password`, `mqtt/username`, `mqtt/password` diretamente da imagem | Firmware / Hardware | Alto | Alta | **Alto** | NIST IR 8259A §3.2; ETSI EN 303 645 §5.4 | Habilitar NVS Encryption no ESP-IDF; usar `nvs_flash_secure_init()` |
| **F10** — Versão "prototype" e informações de build expostas | String `fw_version=0.9.1-prototype` visível no firmware, no log UART e no payload MQTT | Firmware | Baixo | Alta | **Médio** | OWASP ISTG IOT-FW-INFO-002 | Remover identificadores de estágio de desenvolvimento de builds de produção; não expor versão em payloads públicos |

---

## Análise Detalhada por Achado

### F01 — UART Exposta com Log Verbose

**Evidência coletada:**
```
[WIFI] Connecting to SSID: NexaHome_Lab
[WIFI] Password: [REDACTED — visível no dispositivo real]
[NVS] ssid=NexaHome_Lab password=[REDACTED]
[MQTT] Client ID: device001
```

**Fragilidade:** Interface de depuração ativa em modo de operação normal, sem proteção de acesso.

**Possível ameaça:** Atacante com acesso físico ao dispositivo por menos de 30 segundos (reinicialização + leitura serial) obtém credenciais completas da rede Wi-Fi e do broker MQTT.

**Impacto:** Comprometimento da rede Wi-Fi local, acesso ao broker MQTT, possibilidade de injetar dados falsos ou desligar todos os dispositivos NexaSense na instalação.

**Risco: Alto** (Impacto Alto × Probabilidade Alta)

**Relação com referências:**
- *OWASP ISTG IOT-FW-INFO-001:* Interfaces de depuração não devem expor informações sensíveis em modo de produção.
- *ETSI EN 303 645 §5.4:* Parâmetros sensíveis não devem ser armazenados ou transmitidos em texto claro.

---

### F02 — Flash sem Criptografia

**Evidência coletada:**
```bash
$ binwalk nexasense_firmware_working_copy.bin
DECIMAL    HEXADECIMAL    DESCRIPTION
0          0x0            ESP8266/ESP32 bootloader
32768      0x8000         ESP32 partition table
36864      0x9000         ESP32 NVS partition
65536      0x10000        ESP32 application image
```

**Fragilidade:** Flash Encryption não habilitado; imagem legível sem qualquer processo de decriptação.

**Possível ameaça (MITRE EMB3D TEM-0003):** Extração de firmware via interface de hardware (UART/SPI) para engenharia reversa, clonagem ou modificação.

**Impacto:** Exposição completa do código-fonte compilado, de todos os segredos embutidos e da lógica de negócio do dispositivo.

**Risco: Alto** (Impacto Alto × Probabilidade Alta)

**Relação com referências:**
- *MITRE EMB3D TEM-0003:* Extração de firmware via interfaces de hardware é ameaça catalogada para dispositivos sem Flash Encryption.
- *NIST IR 8259A §3.1:* Dispositivos IoT devem possuir mecanismos de proteção de dados armazenados.

---

### F03 / F06 — MQTT sem TLS e Broker sem Autenticação

**Evidência coletada:**
```
# Wireshark — Frame MQTT CONNECT (texto claro)
Client ID: device001
Username: [REDACTED]
Password: [REDACTED]

# Injeção bem-sucedida sem credenciais
$ mosquitto_pub -h 192.168.1.10 -p 1883 -t "/nexasense/device001/cmd" -m '{"cmd":"reboot"}'
# → Sem erro; dispositivo recebeu o comando
```

**Fragilidade:** Protocolo de comunicação sem criptografia de transporte; broker sem controle de acesso.

**Possível ameaça:** Qualquer dispositivo na rede pode interceptar a telemetria de todos os sensores, publicar comandos arbitrários e causar reinicializações, configurações incorretas ou envio de dados falsos à plataforma.

**Impacto:** Perda de confidencialidade dos dados de monitoramento; possível manipulação de alertas e automações dependentes dos dados dos sensores.

**Risco: Alto** (Impacto Alto × Probabilidade Alta)

**Relação com referências:**
- *OWASP ISTG IOT-COM-CRYPT-001 e IOT-COM-AUTH-001:* Comunicações de dispositivos IoT devem usar criptografia de transporte e autenticação.
- *ETSI EN 303 645 §5.8:* Comunicação de dados sensíveis deve ser criptografada.

---

### F05 — OTA via HTTP sem Assinatura

**Evidência coletada:**
```
GET /firmware/nexasense_latest.bin HTTP/1.1
Host: 192.168.1.10:8080
# → Sem TLS; binário transferido sem verificação de integridade
```

**Fragilidade:** Mecanismo de atualização não autentica a origem nem verifica a integridade do firmware baixado.

**Possível ameaça:** Atacante na mesma rede realiza ARP poisoning e serve firmware malicioso. O dispositivo instala sem questionar.

**Impacto:** Comprometimento permanente do dispositivo; possível uso para criar backdoor persistente ou pivot na rede interna.

**Risco: Alto** (Impacto Alto × Probabilidade Média)

**Relação com referências:**
- *OWASP ISTG IOT-FW-UPD-001:* Atualizações de firmware devem ser autenticadas e protegidas contra adulteração.
- *Espressif ESP-IDF Security Docs:* Secure Boot e verificação de assinatura OTA são mecanismos complementares documentados pela fabricante.

---

## Resumo Executivo de Riscos

### Riscos Altos (requerem ação imediata antes de qualquer implantação)

| # | Achado | Ação imediata |
|---|--------|---------------|
| F01 | Log UART com credenciais | Desabilitar logs de produção |
| F02 | Flash sem criptografia | Habilitar Flash Encryption |
| F03 | MQTT sem TLS | Migrar para porta 8883 + TLS |
| F04 | Credenciais hardcoded | Provisionamento em campo |
| F05 | OTA sem assinatura | HTTPS OTA + verificação ECDSA |
| F06 | Broker sem autenticação | Habilitar ACL + TLS mútuo |
| F09 | NVS não criptografada | Habilitar NVS Encryption |

### Riscos Médios (tratar antes da versão comercial)

| # | Achado | Ação |
|---|--------|------|
| F07 | JTAG habilitado | Desabilitar via eFuse em produção |
| F08 | Device ID estático | Identificadores únicos por dispositivo |
| F10 | Versão prototype exposta | Remover identificadores de estágio |

---

## Exemplo Real de Vulnerabilidade Pesquisada

### Caso: Vulnerabilidades no Firmware do Roteador TP-Link Archer C5 (CVE-2021-41450 e relacionados)

**Dispositivo analisado:** TP-Link Archer C5 v4 — roteador Wi-Fi de uso doméstico e comercial amplamente distribuído.

**Superfície de ataque envolvida:** Firmware embarcado + interface de rede (HTTP/telnet).

**Problema identificado:** Pesquisadores da equipe IOACTIVE e do projeto OWASP IoT identificaram que o firmware do roteador continha:
1. **Credenciais hardcoded** no binário do firmware (`admin/admin` e uma senha de serviço técnico oculta).
2. **Interface telnet habilitada por padrão** em alguns modelos, acessível sem autenticação na rede local.
3. **Firmware sem verificação de assinatura** — permitia instalação de versões modificadas via interface web de atualização.
4. **Servidor HTTP interno** com vulnerabilidades de command injection autenticada — mas as credenciais padrão tornavam a autenticação trivial de contornar.

A extração do firmware foi realizada via interface UART exposta no hardware (mesma técnica do NexaSense), revelando as credenciais e a lógica interna do roteador.

**Como o problema poderia ser mitigado:**
- Remoção de credenciais hardcoded e exigência de configuração única por dispositivo no primeiro uso.
- Desabilitação de serviços de depuração (telnet) em builds de produção.
- Assinatura digital de firmware e verificação na instalação.
- Proteção física e lógica da interface UART.

**O que esse caso ensina para o cenário da NexaHome:**

O paralelo com o NexaSense é direto: tanto o roteador TP-Link quanto o protótipo NexaSense mantiveram funcionalidades de desenvolvimento ativas no produto entregue ao usuário final. No caso do roteador, vulnerabilidades descobertas na UART e em credenciais hardcoded permitiram que pesquisadores — e potencialmente atacantes — obtivessem acesso administrativo completo a milhões de dispositivos distribuídos globalmente.

Para a NexaHome, o risco é equivalente mas em um contexto diferente: dispositivos instalados em residências e ambientes comerciais com interfaces físicas acessíveis, credenciais compartilhadas entre todos os dispositivos e comunicação sem criptografia. Um único dispositivo comprometido pode expor a credencial Wi-Fi de toda a instalação do cliente.

A lição central é que **a transição do protótipo para o produto comercial exige uma revisão explícita de segurança**, desabilitando sistematicamente tudo que foi habilitado para conveniência durante o desenvolvimento.

**Fonte:** [IOACTIVE — TP-Link Security Research](https://ioactive.com/tp-link-security-research/); CVE-2021-41450; OWASP IoT Attack Surface Areas.
