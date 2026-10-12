# Análise de Comunicação de Rede — NexaSense

**Data:** 2026-09-30  
**Analista:** NexaHome Security Assessment Team  
**Ambiente:** Rede de laboratório isolada — 192.168.1.0/24  
**Ferramenta principal:** Wireshark 4.2 / tcpdump  
**Captura:** `evidence/nexasense_mqtt_capture.pcapng`

---

## Configuração do Ambiente de Captura

```
[NexaSense ESP32]          [Switch de laboratório]       [PC de análise]
 192.168.1.42      ←──────────── espelhamento ──────────→ 192.168.1.100
        │                                                        │
        └──────────── MQTT TCP:1883 ──────────→ [Broker Mosquitto]
                                                  192.168.1.10
```

**Comando de captura:**
```bash
# Linux
tcpdump -i eth0 -w nexasense_mqtt_capture.pcapng "host 192.168.1.42"

# Ou diretamente no Wireshark com filtro:
# ip.addr == 192.168.1.42 && tcp.port == 1883
```

---

## Etapa 1 — Identificação do Protocolo

### Descoberta
Ao iniciar a captura e ligar o NexaSense, observou-se imediatamente conexão TCP na **porta 1883** ao endereço `192.168.1.10`.

O Wireshark dissecou automaticamente o tráfego como **MQTT 3.1.1** — protocolo de mensageria leve para IoT baseado em publish/subscribe.

### Protocolo identificado: MQTT 3.1.1
- **Camada de transporte:** TCP
- **Porta:** 1883 (plaintext — **sem TLS**)
- **Porta segura padrão MQTT:** 8883 (MQTTS) — **não utilizada**

### Diferença entre identificar o protocolo e avaliar sua segurança
> Identificar que o dispositivo usa MQTT é apenas o primeiro passo.  
> A questão crítica é: **o uso desse protocolo é seguro neste contexto?**
>
> MQTT é um protocolo válido para IoT. O problema não é o protocolo em si, mas:
> - Uso da **porta 1883 (plaintext)** em vez de 8883 (TLS)
> - Broker configurado com **`allow_anonymous true`** (sem autenticação)
> - **Payload em JSON sem qualquer criptografia ou assinatura**
>
> Um dispositivo pode usar MQTT de forma segura com TLS mútuo, certificados por dispositivo e ACLs no broker. O NexaSense não implementa nenhuma dessas camadas.

---

## Etapa 2 — Análise do Handshake MQTT

### Fluxo capturado — CONNECT

```
Frame 1: [NexaSense → Broker] TCP SYN
Frame 2: [Broker → NexaSense] TCP SYN-ACK
Frame 3: [NexaSense → Broker] TCP ACK

Frame 4: [NexaSense → Broker] MQTT CONNECT
  ├── Protocol Name: MQTT
  ├── Protocol Level: 4 (MQTT 3.1.1)
  ├── Client ID: device001
  ├── Clean Session: 1
  ├── Keep Alive: 60s
  ├── User Name Flag: 1
  ├── Password Flag: 1
  ├── Username: [REDACTED]     ← transmitido em TEXTO CLARO
  └── Password: [REDACTED]     ← transmitido em TEXTO CLARO

Frame 5: [Broker → NexaSense] MQTT CONNACK
  └── Return Code: 0x00 (Connection Accepted)
```

### Observação crítica
As credenciais MQTT (`username` e `password`) são transmitidas em texto claro no pacote CONNECT. Qualquer dispositivo na mesma rede de laboratório pode capturar essas credenciais com Wireshark — sem necessidade de qualquer ataque ativo.

---

## Etapa 3 — Análise das Mensagens de Telemetria

### Tópico de publicação
```
/nexasense/device001/telemetry
```

### Payload capturado (JSON — texto claro)
```json
{
  "device_id": "device001",
  "temp": 24.5,
  "hum": 62.3,
  "ts": 1727737200
}
```

### Frequência de publicação
Mensagem publicada a cada **30 segundos** (configurado no firmware).

### Tópico de comandos (subscribe)
```
/nexasense/device001/cmd
```
O dispositivo assina este tópico para receber comandos remotos. Qualquer cliente na rede pode publicar neste tópico e enviar comandos ao dispositivo, pois o broker não possui ACL configurada.

---

## Etapa 4 — Verificação de Autenticação, Confidencialidade e Integridade

### 4.1 Autenticação

| Mecanismo                  | Implementado? | Observação                                        |
|----------------------------|---------------|---------------------------------------------------|
| TLS mútuo (certificados)   | ❌ Não        | Sem certificado cliente nem CA configurados       |
| Username/Password MQTT     | ⚠️ Parcial   | Campos presentes mas transmitidos em texto claro  |
| ACL no broker              | ❌ Não        | `allow_anonymous true` no mosquitto.conf          |
| Certificado por dispositivo| ❌ Não        | Todos os dispositivos usariam as mesmas credenciais|

### 4.2 Confidencialidade

| Dado transmitido           | Criptografado? | Risco                                             |
|----------------------------|----------------|---------------------------------------------------|
| Credenciais MQTT           | ❌ Não         | Visíveis em qualquer captura de rede              |
| Payload de telemetria      | ❌ Não         | Dados de temperatura/umidade legíveis             |
| Device ID                  | ❌ Não         | Identificador do dispositivo exposto              |
| Timestamp                  | ❌ Não         | Permite inferência de padrões de uso              |

### 4.3 Integridade

| Mecanismo                  | Implementado? | Observação                                        |
|----------------------------|---------------|---------------------------------------------------|
| Assinatura de mensagens    | ❌ Não        | Nenhuma verificação de que a mensagem é autêntica |
| HMAC no payload            | ❌ Não        | Payload pode ser forjado                          |
| Sequence number / replay   | ❌ Não        | Mensagens podem ser capturadas e reenviadas       |

---

## Etapa 5 — Exposição de Identificadores

### Device ID previsível
O campo `device_id` no payload e o `Client ID` MQTT são ambos `device001` — identificador sequencial estático.

**Implicação:** Em um deployment com múltiplos dispositivos, os IDs seriam `device001`, `device002`, etc., permitindo a um atacante:
- Enumerar todos os dispositivos na plataforma
- Subscrever tópicos de outros dispositivos (`/nexasense/device002/telemetry`)
- Publicar comandos forjados para qualquer dispositivo

### Exposição do timestamp
O campo `ts` (Unix timestamp) expõe informações sobre o horário de funcionamento do dispositivo, podendo ser usado para rastrear padrões de presença em um ambiente residencial.

---

## Etapa 6 — Demonstração Controlada: Injeção de Mensagem MQTT

**Objetivo:** Demonstrar que qualquer cliente na rede pode publicar mensagens no tópico de comandos do dispositivo.

**Ferramenta:** cliente MQTT `mosquitto_pub`

```bash
# Publicar comando forjado ao dispositivo (sem autenticação necessária)
mosquitto_pub -h 192.168.1.10 -p 1883 \
  -t "/nexasense/device001/cmd" \
  -m '{"cmd":"reboot","source":"attacker"}'

# Ou assinar o tópico de telemetria para receber todos os dados
mosquitto_sub -h 192.168.1.10 -p 1883 \
  -t "/nexasense/#" -v
```

**Resultado:** O broker aceita a publicação sem qualquer autenticação. O dispositivo recebe o comando. Um atacante pode forçar reinicializações, alterar configurações ou injetar leituras falsas de sensor.

**Evidência:** `evidence/mqtt-inject-demo.png` — captura da sessão mostrando o comando aceito.

---

## Etapa 7 — Análise do Mecanismo OTA via Rede

### Comportamento observado
Quando o dispositivo verifica por atualizações (acionado pelo tópico de comandos), faz uma requisição HTTP GET:

```
GET /firmware/nexasense_latest.bin HTTP/1.1
Host: 192.168.1.10:8080
User-Agent: esp-idf/1.0 esp32
```

### Problemas identificados
1. **HTTP puro** — sem TLS, o tráfego pode ser interceptado e o binário substituído (MitM).
2. **Sem verificação de assinatura** — o dispositivo não verifica se o firmware baixado é autêntico.
3. **Sem verificação de versão** — pode ser feito downgrade para versão vulnerável anterior.

### Demonstração conceitual — MitM OTA
```
Atacante configura servidor HTTP falso na mesma rede:
  192.168.1.200:8080/firmware/nexasense_latest.bin → firmware malicioso

Redireciona DNS ou ARP para o servidor falso.
Dispositivo baixa e instala firmware malicioso sem qualquer verificação.
```

---

## Resumo dos Achados de Rede

| ID  | Achado                                      | Evidência                                    | Impacto | Probabilidade | Risco  |
|-----|---------------------------------------------|----------------------------------------------|---------|---------------|--------|
| N01 | MQTT sem TLS (porta 1883)                   | Captura Wireshark — tráfego legível          | Alto    | Alta          | Alto   |
| N02 | Broker sem autenticação / ACL               | `allow_anonymous true` — comando injetado    | Alto    | Alta          | Alto   |
| N03 | Credenciais MQTT em texto claro na rede     | Pacote CONNECT capturado                     | Alto    | Alta          | Alto   |
| N04 | OTA via HTTP sem assinatura de firmware     | Requisição GET sem TLS observada             | Alto    | Média         | Alto   |
| N05 | Device ID estático e enumerável             | `device001` no payload e Client ID          | Médio   | Alta          | Médio  |
| N06 | Timestamp expõe padrões de uso             | Campo `ts` no JSON de telemetria             | Baixo   | Alta          | Baixo  |
