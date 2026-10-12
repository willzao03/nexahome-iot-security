# Análise de Firmware — NexaSense v0.9.1

**Data:** 2026-09-30  
**Analista:** NexaHome Security Assessment Team  
**Arquivo analisado:** `nexasense_firmware_working_copy.bin` (cópia de trabalho)  
**Hash SHA-256:** `a3f8c1d2e94b57062f1a8390dc4e27b5f6083c91ad254e78b1f9302e6c7d4158`

---

## Etapa 1 — Identificação do Formato e Estrutura

### Comando
```bash
binwalk nexasense_firmware_working_copy.bin
```

### Resultado
```
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
0             0x0             ESP8266/ESP32 bootloader, total size: 28672
32768         0x8000          ESP32 partition table (MD5 verified)
36864         0x9000          ESP32 NVS (Non-Volatile Storage) partition
65536         0x10000         ESP32 application image (IDF v5.1.2)
65548         0x1000C         LZMA compressed data, properties: 0x5D
1245184       0x130000        ESP32 OTA data partition
```

### Observações
- Formato **IDF Application Image** padrão, sem criptografia de flash ativa.
- A ausência de Flash Encryption é imediatamente perceptível: binwalk consegue identificar e analisar todas as estruturas sem qualquer processo de decriptação.
- O bootloader é o stage2 padrão do ESP-IDF, sem Secure Boot habilitado (sem assinatura RSA/ECDSA no header).

---

## Etapa 2 — Análise da Tabela de Partições

### Comando
```bash
python3 -m esp_idf_size --format json nexasense_firmware_working_copy.bin
# ou leitura direta via esptool:
esptool.py --port /dev/ttyUSB0 read_flash 0x8000 0xC00 partition_table.bin
python3 $IDF_PATH/components/partition_table/gen_esp32part.py partition_table.bin
```

### Tabela de Partições Reconstruída

| Nome       | Tipo | Subtipo | Offset   | Tamanho   | Flags |
|------------|------|---------|----------|-----------|-------|
| nvs        | data | nvs     | 0x009000 | 0x006000  |       |
| phy_init   | data | phy     | 0x00F000 | 0x001000  |       |
| factory    | app  | factory | 0x010000 | 0x140000  |       |
| ota_0      | app  | ota_0   | 0x150000 | 0x140000  |       |
| ota_data   | data | ota     | 0x290000 | 0x002000  |       |

### Observações de Segurança
- Partição **NVS não criptografada**: armazena parâmetros de configuração, incluindo credenciais Wi-Fi e parâmetros MQTT em texto claro.
- Dois slots OTA (`factory` + `ota_0`) sem mecanismo de rollback seguro documentado.
- Sem partição de armazenamento seguro (`nvs_encrypted`).

---

## Etapa 3 — Extração de Strings e Informações Sensíveis

### Comando
```bash
strings nexasense_firmware_working_copy.bin | grep -iE \
  "(ssid|password|passwd|wifi|mqtt|http|192\.168|token|secret|key|debug|version)" \
  | sort -u
```

### Strings Relevantes Encontradas

> ⚠️ Os valores reais de credenciais foram substituídos por `[REDACTED]` neste repositório.

```
# Credenciais Wi-Fi (hardcoded no firmware)
NEXAHOME_WIFI_SSID=[REDACTED]
NEXAHOME_WIFI_PASS=[REDACTED]

# Configuração MQTT
mqtt://192.168.1.10:1883
/nexasense/device001/telemetry
/nexasense/device001/cmd
mqtt_user=[REDACTED]
mqtt_pass=[REDACTED]

# Endpoint OTA
http://192.168.1.10:8080/firmware/nexasense_latest.bin

# Identificadores e versão
device_id=device001
fw_version=0.9.1-prototype
hw_revision=ESP32-WROOM-32D

# Mensagens de debug (verbose)
[BOOT] Starting NexaSense firmware v0.9.1
[WIFI] Connecting to SSID: %s
[WIFI] Connected! IP: %s
[MQTT] Connecting to broker: %s
[MQTT] Connected to broker
[MQTT] Publishing: %s -> %s
[OTA] Starting OTA update from: %s
[OTA] OTA progress: %d%%
[SENSOR] Temp=%.1f Hum=%.1f
[NVS] Loading config from NVS...
[NVS] ssid=%s password=%s
[ERROR] MQTT connection failed, retrying...
```

### Análise das Strings

| String encontrada               | Relevância de Segurança                                                       |
|---------------------------------|-------------------------------------------------------------------------------|
| `NEXAHOME_WIFI_SSID/PASS`       | **Crítico** — credenciais Wi-Fi hardcoded, expostas a qualquer um que extraia o firmware |
| `mqtt://192.168.1.10:1883`      | **Alto** — broker sem TLS (`mqtt://` em vez de `mqtts://`)                   |
| `mqtt_user` / `mqtt_pass`       | **Alto** — credenciais MQTT em texto claro no binário                        |
| `http://...nexasense_latest.bin`| **Alto** — OTA via HTTP sem verificação de assinatura                        |
| `device_id=device001`           | **Médio** — identificador estático e previsível, sem unicidade por dispositivo |
| `[NVS] ssid=%s password=%s`     | **Médio** — log de debug imprime credenciais na UART                         |
| `fw_version=0.9.1-prototype`    | **Baixo** — versão "prototype" exposta facilita reconhecimento do atacante   |

---

## Etapa 4 — Verificação do Mecanismo OTA

### Análise
O firmware implementa OTA via **HTTP simples** utilizando a API `esp_https_ota` do ESP-IDF, porém configurada com `use_global_ca_store = false` e sem certificado raiz configurado — efetivamente usando HTTP em vez de HTTPS.

```c
// Trecho reconstruído por análise de strings e comportamento observado
esp_http_client_config_t config = {
    .url = "http://192.168.1.10:8080/firmware/nexasense_latest.bin",
    .cert_pem = NULL,  // SEM verificação TLS
};
esp_https_ota_config_t ota_config = {
    .http_config = &config,
};
// Sem verificação de assinatura RSA/ECDSA da imagem
esp_https_ota(&ota_config);
```

### Impacto
Um atacante na mesma rede pode realizar um **ataque Man-in-the-Middle** para substituir a imagem de firmware por uma versão maliciosa. O dispositivo instalará o firmware sem qualquer validação de autenticidade ou integridade.

---

## Etapa 5 — Análise da Partição NVS

### Observação
A partição NVS foi extraída e analisada com `nvs_flash_read` (simulado via ferramenta `nvs_partition_parser`):

```bash
python3 nvs_partition_parser.py nvs_partition.bin
```

### Conteúdo encontrado na NVS

| Namespace | Chave        | Tipo   | Valor                    |
|-----------|--------------|--------|--------------------------|
| wifi      | ssid         | string | [REDACTED]               |
| wifi      | password     | string | [REDACTED]               |
| mqtt      | broker_url   | string | mqtt://192.168.1.10:1883 |
| mqtt      | client_id    | string | device001                |
| mqtt      | username     | string | [REDACTED]               |
| mqtt      | password     | string | [REDACTED]               |
| device    | fw_version   | string | 0.9.1-prototype          |
| device    | hw_revision  | string | ESP32-WROOM-32D          |

**Sem NVS Encryption** — todos os valores são legíveis diretamente na imagem binária.

---

## Resumo dos Achados do Firmware

| ID  | Achado                                    | Evidência                                         | Impacto |
|-----|-------------------------------------------|---------------------------------------------------|---------|
| F01 | Credenciais Wi-Fi hardcoded               | Strings `NEXAHOME_WIFI_SSID/PASS` no binário      | Alto    |
| F02 | Flash sem criptografia                    | binwalk analisa estrutura sem decriptação          | Alto    |
| F03 | OTA via HTTP sem verificação de assinatura| URL `http://` + sem certificado raiz              | Alto    |
| F04 | NVS não criptografada                     | Credenciais legíveis na partição NVS              | Alto    |
| F05 | Mensagens de debug verbose                | Strings `[NVS] ssid=%s password=%s` no log        | Médio   |
| F06 | Device ID estático (`device001`)          | String hardcoded no firmware e na NVS             | Médio   |
| F07 | Versão "prototype" exposta                | String `fw_version=0.9.1-prototype`               | Baixo   |
