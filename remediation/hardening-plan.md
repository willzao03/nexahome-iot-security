# Plano de Hardening — NexaSense Versão Comercial

**Data:** 2026-09-30  
**Baseado em:** ETSI EN 303 645 v3.1.3, NIST IR 8259A, Espressif ESP-IDF Security Docs, OWASP ISTG  
**Escopo:** Medidas técnicas e de processo para transição do protótipo NexaSense para versão comercial segura  
**Nota:** As medidas marcadas com ⚠️ são **irreversíveis** no hardware ESP32 — devem ser executadas apenas em produção, após validação completa.

---

## Visão Geral — Prioridades de Hardening

```
PRIORIDADE 1 (Bloqueadores — não lançar sem estas medidas)
├── H01 Flash Encryption
├── H02 Secure Boot v2
├── H03 MQTT sobre TLS 1.3
├── H04 Remoção de credenciais hardcoded
└── H05 Assinatura de firmware OTA

PRIORIDADE 2 (Alta importância — implementar no ciclo de lançamento)
├── H06 NVS Encryption
├── H07 Desabilitar JTAG em produção ⚠️
├── H08 Desabilitar UART download mode ⚠️
├── H09 Autenticação por dispositivo (certificados)
└── H10 Redução de logs em produção

PRIORIDADE 3 (Melhoria contínua — versões subsequentes)
├── H11 Device ID único por dispositivo
├── H12 Processo seguro de atualização (FOTA)
├── H13 Proteção física da placa
└── H14 Política de divulgação e resposta a vulnerabilidades
```

---

## H01 — Flash Encryption (⚠️ Irreversível em produção)

**Problema endereçado:** F02, F09 — firmware e NVS extraíveis em texto claro via UART/SPI  
**Referência:** Espressif ESP-IDF Security Docs; NIST IR 8259A §3.1

### O que faz
O ESP32 suporta criptografia AES-256 da flash SPI. Quando habilitado, todo o conteúdo da flash (firmware, NVS, partição de dados) é criptografado com uma chave única gerada no primeiro boot e armazenada nos eFuses do chip. Mesmo que o atacante extraia o chip SPI ou use `esptool.py`, o conteúdo é ilegível.

### Como habilitar (ESP-IDF)
```bash
# No menuconfig do projeto
idf.py menuconfig
# → Security Features
#   → Enable flash encryption on boot: YES
#   → Flash encryption mode: Release (produção) / Development (testes)
```

### Configuração de produção (`sdkconfig`)
```
CONFIG_FLASH_ENCRYPTION_ENABLED=y
CONFIG_FLASH_ENCRYPTION_MODE_RELEASE=y
# Modo Release: desabilita regravação não autorizada da flash
```

### Advertências importantes
- Em **modo Release**, a flash só pode ser atualizada via OTA autenticado — não via `esptool.py`.
- A chave de criptografia é gerada aleatoriamente no primeiro boot e **não pode ser recuperada**.
- Habilitar Flash Encryption sem Secure Boot ainda permite que firmware não assinado seja instalado via OTA — ambos devem ser usados juntos.

---

## H02 — Secure Boot v2 (⚠️ Irreversível em produção)

**Problema endereçado:** F02, F05 — firmware pode ser substituído sem autenticação  
**Referência:** Espressif ESP-IDF Security Docs; ETSI EN 303 645 §5.3

### O que faz
Secure Boot v2 usa RSA-PSS 3072-bit ou ECDSA para assinar imagens de firmware. O bootloader verifica a assinatura antes de executar qualquer aplicação. Firmware não assinado pela chave privada da NexaHome é recusado.

### Fluxo de implementação
```
1. Gerar par de chaves RSA-3072 (chave privada armazenada offline, segura)
   openssl genrsa -out secure_boot_signing_key.pem 3072

2. Configurar no ESP-IDF
   idf.py menuconfig
   → Security Features → Enable Secure Boot
   → Secure Boot Signing Key: ./secure_boot_signing_key.pem
   → Secure Boot v2: YES

3. Build e primeiro flash (queima a chave pública nos eFuses)
   idf.py build flash

4. Todos os firmwares OTA futuros devem ser assinados com a mesma chave privada
   espsecure.py sign_data --version 2 --keyfile secure_boot_signing_key.pem \
     --output firmware_signed.bin firmware.bin
```

### Proteção da chave privada
- A chave privada RSA **jamais deve ser incluída no repositório de código**.
- Deve ser armazenada em HSM (Hardware Security Module) ou vault seguro (ex.: AWS Secrets Manager, HashiCorp Vault).
- Acesso à chave deve ser restrito ao pipeline de CI/CD de produção com autenticação multifator.

---

## H03 — MQTT sobre TLS 1.3 com Autenticação por Certificado

**Problema endereçado:** F03, F06 — tráfego MQTT em texto claro; broker sem autenticação  
**Referência:** OWASP ISTG IOT-COM-CRYPT-001; ETSI EN 303 645 §5.8

### Arquitetura proposta
```
[NexaSense]                    [Broker MQTT]
     │                              │
     │  TLS 1.3 (porta 8883)        │
     │  Cert cliente: device001.crt │
     │  CA: nexahome-ca.crt         │
     ├──────────────────────────────►
     │  CONNACK (autenticado)        │
```

### Configuração no firmware (ESP-IDF)
```c
// Certificado CA da NexaHome (embarcado no firmware como string PEM)
extern const char nexahome_ca_pem[] asm("_binary_nexahome_ca_pem_start");
// Certificado do dispositivo (único por dispositivo)
extern const char device_cert_pem[] asm("_binary_device_cert_pem_start");
// Chave privada do dispositivo (armazenada na NVS criptografada)
extern const char device_key_pem[] asm("_binary_device_key_pem_start");

esp_mqtt_client_config_t mqtt_cfg = {
    .broker = {
        .address.uri = "mqtts://mqtt.nexahome.com.br:8883",
        .verification.certificate = nexahome_ca_pem,
    },
    .credentials = {
        .authentication = {
            .certificate = device_cert_pem,
            .key = device_key_pem,
        },
    },
};
```

### Configuração do broker Mosquitto (produção)
```
# /etc/mosquitto/mosquitto.conf
listener 8883
cafile /etc/mosquitto/ca/nexahome-ca.crt
certfile /etc/mosquitto/certs/broker.crt
keyfile /etc/mosquitto/certs/broker.key
require_certificate true   # TLS mútuo obrigatório
allow_anonymous false
use_identity_as_username true  # CN do certificado como username

# ACL
acl_file /etc/mosquitto/acls.conf
```

```
# /etc/mosquitto/acls.conf
# Cada dispositivo só pode publicar/assinar seus próprios tópicos
pattern readwrite /nexasense/%u/#
```

---

## H04 — Remoção de Credenciais Hardcoded — Provisionamento em Campo

**Problema endereçado:** F01, F04 — SSID/senha Wi-Fi e credenciais MQTT compilados no firmware  
**Referência:** ETSI EN 303 645 §5.1; NIST IR 8259A §3.2

### Solução proposta: Provisionamento via BLE (Bluetooth Low Energy)

O ESP-IDF fornece o componente `wifi_provisioning` que permite configurar o dispositivo via BLE no primeiro uso, sem credenciais hardcoded:

```c
// No firmware — primeiro boot sem credenciais configuradas
wifi_prov_mgr_config_t config = {
    .scheme = wifi_prov_scheme_ble,
    .scheme_event_handler = WIFI_PROV_SCHEME_BLE_EVENT_HANDLER_FREE_BTDM,
};
wifi_prov_mgr_init(config);

// Dispositivo anuncia-se via BLE
// App mobile da NexaHome configura SSID + senha + endpoint MQTT
// Credenciais armazenadas na NVS criptografada
```

### Benefícios
- Nenhuma credencial no binário de firmware — mesmo dispositivos clonados não funcionam na rede do cliente.
- Cada dispositivo pode ter credenciais MQTT únicas.
- Suporte a reconfiguração sem reflash (botão de reset de provisionamento).

---

## H05 — Assinatura e Verificação de Firmware OTA

**Problema endereçado:** F05 — OTA via HTTP sem verificação de integridade  
**Referência:** OWASP ISTG IOT-FW-UPD-001; ETSI EN 303 645 §5.3

### Implementação com ESP-IDF `esp_https_ota`

```c
// OTA seguro com verificação TLS e assinatura (requer Secure Boot v2 habilitado)
esp_http_client_config_t http_config = {
    .url = "https://ota.nexahome.com.br/firmware/nexasense_latest.bin",
    .cert_pem = nexahome_ota_ca_pem,  // CA do servidor OTA
    .timeout_ms = 10000,
};

esp_https_ota_config_t ota_config = {
    .http_config = &http_config,
};

// Com Secure Boot v2 habilitado, a verificação de assinatura é automática
esp_err_t ret = esp_https_ota(&ota_config);
if (ret == ESP_OK) {
    esp_restart();  // Aplica o novo firmware
} else {
    ESP_LOGE(TAG, "OTA falhou: %s", esp_err_to_name(ret));
    // NÃO reiniciar — manter firmware atual
}
```

### Estratégia de rollback
- O ESP-IDF suporta partições OTA duplas (`ota_0` e `ota_1`).
- Após atualização, o dispositivo marca a partição como pendente de validação.
- Se o novo firmware falhar (watchdog, panic), o bootloader reverte automaticamente para a partição anterior.
- A NexaHome deve implementar um heartbeat de confirmação: firmware novo envia confirmação ao servidor após boot bem-sucedido.

---

## H06 — NVS Encryption

**Problema endereçado:** F04, F09 — credenciais legíveis na partição NVS  
**Referência:** NIST IR 8259A §3.2

### Implementação
```c
// Inicialização com NVS criptografada (ESP-IDF 5.x)
nvs_sec_cfg_t cfg;
// Gerar chave de NVS armazenada em partição de chaves na flash
esp_err_t err = nvs_flash_generate_keys(&cfg);
if (err == ESP_OK) {
    nvs_flash_secure_init(&cfg);
}
```

A chave de criptografia da NVS é armazenada em uma partição separada, protegida pelo Flash Encryption — cadeia de proteção complementar.

---

## H07 — Desabilitar JTAG em Produção (⚠️ Irreversível)

**Problema endereçado:** F07 — pinos JTAG acessíveis permitem depuração não autorizada  
**Referência:** MITRE EMB3D; OWASP ISTG IOT-HW-DEBUG-001

```c
// Desabilitar JTAG via eFuse (ESP-IDF)
// ATENÇÃO: operação IRREVERSÍVEL — executar apenas em linha de produção
#include "esp_efuse.h"

void disable_debug_interfaces_for_production(void) {
    // Desabilitar JTAG
    esp_efuse_disable_jtag();
    // Desabilitar UART download mode
    esp_efuse_disable_uart_download_mode();
    ESP_LOGI(TAG, "Interfaces de depuração desabilitadas (produção)");
}
```

**Processo recomendado na linha de produção:**
1. Fazer flash do firmware assinado.
2. Executar testes funcionais completos.
3. **Somente após validação**: executar a queima dos eFuses.
4. Verificar que o dispositivo ainda funciona corretamente após a queima.

---

## H08 — Redução de Informações de Debug em Produção

**Problema endereçado:** F01, F10 — logs verbose com credenciais; versão "prototype" exposta  
**Referência:** ETSI EN 303 645 §5.4; OWASP ISTG IOT-FW-INFO-001

### Configuração `sdkconfig` para produção
```
# Desabilitar todos os logs (ou manter apenas erros críticos)
CONFIG_LOG_DEFAULT_LEVEL_NONE=y
# Ou, para manter apenas erros sem dados sensíveis:
CONFIG_LOG_DEFAULT_LEVEL_ERROR=y

# Nunca usar em produção:
# CONFIG_LOG_DEFAULT_LEVEL_DEBUG=y  ← usado no protótipo
# CONFIG_LOG_DEFAULT_LEVEL_VERBOSE=y
```

### Regras de codificação para logs
```c
// PROIBIDO em qualquer nível de log
ESP_LOGI(TAG, "[NVS] ssid=%s password=%s", ssid, password);  // NUNCA

// PERMITIDO — sem dados sensíveis
ESP_LOGI(TAG, "[WIFI] Conexão estabelecida");
ESP_LOGE(TAG, "[MQTT] Falha na conexão: %d", err_code);
```

---

## H09 — Device ID Único por Dispositivo

**Problema endereçado:** F08 — device ID estático permite enumeração  
**Referência:** NIST IR 8259A §3.1; ETSI EN 303 645 §5.1

### Solução
```c
// Usar MAC address do ESP32 como base para UUID único
uint8_t mac[6];
esp_wifi_get_mac(WIFI_IF_STA, mac);
char device_id[37];
snprintf(device_id, sizeof(device_id),
    "nexasense-%02x%02x%02x%02x%02x%02x",
    mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
// Resultado: "nexasense-a4cf121b3e8f" — único por dispositivo
```

---

## H10 — Proteção Física da Placa (Design de Produto)

**Problema endereçado:** F01, F02, F07 — interfaces físicas acessíveis  
**Referência:** ETSI EN 303 645; MITRE EMB3D

### Medidas de design para versão comercial

| Medida | Descrição | Custo |
|--------|-----------|-------|
| Remoção de headers | Não incluir conectores de debug na PCB de produção | Baixo |
| Potting / resina epóxi | Cobrir componentes críticos com resina para dificultar acesso físico | Médio |
| Enclosure com lacre | Caixa plástica com etiqueta de violação visível (tamper evident) | Médio |
| Remoção de pads de teste | Não expor pads JTAG e UART na placa de produção | Baixo (design) |
| PCB de camada interna | Rotear trilhas sensíveis em camadas internas do PCB | Médio |

---

## Resumo do Plano de Hardening

| ID  | Medida                          | Prioridade | Esforço | Impacto nos Riscos              |
|-----|---------------------------------|------------|---------|----------------------------------|
| H01 | Flash Encryption                | Crítica    | Médio   | Elimina F02, F09                |
| H02 | Secure Boot v2                  | Crítica    | Médio   | Elimina F05, complementa H01    |
| H03 | MQTT sobre TLS 1.3              | Crítica    | Alto    | Elimina F03, F06                |
| H04 | Remoção de credenciais          | Crítica    | Alto    | Elimina F04                     |
| H05 | Assinatura OTA                  | Crítica    | Médio   | Elimina F05                     |
| H06 | NVS Encryption                  | Alta       | Baixo   | Reduz F04, F09                  |
| H07 | Desabilitar JTAG ⚠️             | Alta       | Baixo   | Elimina F07                     |
| H08 | Reduzir logs de produção        | Alta       | Baixo   | Elimina F01, F10                |
| H09 | Device ID único                 | Média      | Baixo   | Elimina F08                     |
| H10 | Proteção física                 | Média      | Médio   | Reduz F01, F02, F07             |

### Estado de segurança projetado após hardening

```
ANTES (protótipo)          DEPOIS (comercial)
─────────────────          ───────────────────
Flash: legível        →    Flash: AES-256 criptografada
MQTT: texto claro     →    MQTT: TLS 1.3 + cert por dispositivo
OTA: HTTP sem assin.  →    HTTPS OTA + verificação ECDSA
Credenciais: hardcoded→    Provisionamento BLE em campo
JTAG: habilitado      →    JTAG: desabilitado via eFuse
Logs: verbose         →    Logs: desabilitados em produção
Device ID: estático   →    Device ID: UUID baseado em MAC
```
