# Evidências — Análise de Rede

Esta pasta contém as evidências coletadas durante a análise de comunicação do NexaSense.

## Arquivos Esperados

| Arquivo                          | Descrição                                                           |
|----------------------------------|---------------------------------------------------------------------|
| `nexasense_mqtt_capture.pcapng`  | Captura Wireshark do tráfego MQTT (sessão completa de boot)         |
| `mqtt-connect-packet.png`        | Screenshot do pacote MQTT CONNECT com credenciais visíveis          |
| `mqtt-telemetry-payload.png`     | Screenshot do payload de telemetria em texto claro                  |
| `mqtt-inject-demo.png`           | Screenshot da injeção de comando via mosquitto_pub                  |
| `wireshark-filter-mqtt.png`      | Screenshot do Wireshark com filtro MQTT aplicado                    |

## Filtros Wireshark Úteis

```
# Todo o tráfego MQTT
mqtt

# Apenas mensagens PUBLISH
mqtt.msgtype == 3

# Apenas pacotes do dispositivo
ip.src == 192.168.1.42 && mqtt

# Filtrar por tópico específico
mqtt.topic contains "nexasense"
```

## Notas

- Credenciais MQTT observadas na captura foram **redatadas** nas capturas publicadas.
- A captura `.pcapng` original não deve ser publicada no repositório se contiver credenciais reais.
