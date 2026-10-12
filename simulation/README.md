# Ambiente de Simulação — NexaSense

Ambiente de laboratório em Python para quem **não possui o hardware ESP32**.  
Reproduz fielmente as evidências que seriam coletadas com o dispositivo físico.

---

## Pré-requisitos

```powershell
# Python 3.11+ (já instalado)
python --version

# Dependência MQTT
pip install paho-mqtt

# Broker Mosquitto (para scripts MQTT)
winget install mosquitto
```

---

## Ordem de Execução

Execute cada script na pasta `simulation/` nesta ordem:

### Passo 1 — Log de Boot UART
```powershell
cd simulation
python 01_uart_boot_simulation.py --save
```
**O que faz:** Simula a saída serial do ESP32 no boot, revelando credenciais Wi-Fi
e MQTT em texto claro — evidência do achado F01.  
**Gera:** `hardware/evidence/uart-boot-log.txt`

---

### Passo 2 — Gerar firmware .bin + hashes
```powershell
python 04_firmware_generator.py
```
**O que faz:** Cria uma imagem binária de 4 MB com estrutura ESP32 real
(bootloader, partition table, NVS com credenciais, app com strings sensíveis).  
**Gera:** `firmware/nexasense_firmware_original.bin` + atualiza `firmware/hashes.txt`

---

### Passo 3 — Análise estática do firmware
```powershell
python 05_firmware_analysis.py --save
```
**O que faz:** Executa análise equivalente a `binwalk` + `strings` sobre o .bin,
extraindo credenciais, endpoints, mensagens de debug e metadados sensíveis.  
**Gera:** `firmware/analysis-notes-generated.md`

---

### Passo 4 — Broker MQTT local (terminal separado)
```powershell
# Abrir um NOVO terminal PowerShell e executar:
mosquitto -v
```
**Mantenha este terminal aberto** para os próximos passos.

---

### Passo 5 — Dispositivo publicando telemetria (terminal separado)
```powershell
# Em outro terminal:
cd simulation
python 02_device_mqtt_simulator.py --count 10
```
**O que faz:** Simula o ESP32 conectando ao broker sem TLS e publicando
dados de sensor em JSON sem criptografia.  
**Gera:** `network/evidence/mqtt-telemetry-payload.txt`

---

### Passo 6 — Demonstração de ataque (terminal separado)
```powershell
# Em outro terminal (enquanto o passo 5 roda):
cd simulation
python 03_attacker_mqtt_inject.py
```
**O que faz:** Simula um atacante na mesma rede interceptando a telemetria
e injetando comandos arbitrários sem autenticação.  
**Gera:** `network/evidence/mqtt-inject-demo.txt`

---

## Captura Wireshark (opcional mas recomendado)

Para capturar o tráfego MQTT visualmente:

1. Abrir **Wireshark**
2. Selecionar interface **Loopback** (`\Device\NPF_Loopback` no Windows)  
   *(se não aparecer: instalar Npcap em https://npcap.com)*
3. Filtro: `mqtt`
4. Executar os passos 4, 5 e 6 acima
5. Observar pacotes CONNECT (com usuário/senha visíveis) e PUBLISH (payload JSON)
6. **File → Export Specified Packets** → salvar como `network/evidence/nexasense_mqtt_capture.pcapng`

---

## Resumo — Evidências Geradas

| Arquivo | Script | Achado demonstrado |
|---------|--------|-------------------|
| `hardware/evidence/uart-boot-log.txt` | 01 | F01 — UART com credenciais |
| `firmware/nexasense_firmware_original.bin` | 04 | F02 — Flash sem criptografia |
| `firmware/hashes.txt` | 04 | Integridade da imagem |
| `firmware/analysis-notes-generated.md` | 05 | F04, F05, F09 — strings sensíveis |
| `network/evidence/mqtt-telemetry-payload.txt` | 02 | F03 — MQTT sem TLS |
| `network/evidence/mqtt-inject-demo.txt` | 03 | F06 — Broker sem autenticação |

---

## Estrutura dos Scripts

```
simulation/
├── README.md                      ← este arquivo
├── 01_uart_boot_simulation.py     ← log de boot com credenciais
├── 02_device_mqtt_simulator.py    ← dispositivo publicando telemetria
├── 03_attacker_mqtt_inject.py     ← atacante interceptando e injetando
├── 04_firmware_generator.py       ← gerador de firmware .bin simulado
└── 05_firmware_analysis.py        ← análise estática (binwalk + strings)
```
