"""
Apresentacao do trabalho — rodar antes de tudo no video
"""

texto = """
╔══════════════════════════════════════════════════════════════════╗
║     DO PROTÓTIPO AO PRODUTO SEGURO                              ║
║     Avaliação de Segurança de um Dispositivo IoT                ║
║     NexaHome Technologies — NexaSense ESP32                     ║
╚══════════════════════════════════════════════════════════════════╝

  Este trabalho apresenta uma avaliação de segurança estruturada
  do protótipo NexaSense, dispositivo IoT baseado no ESP32-WROOM-32D
  que coleta temperatura e umidade e transmite dados via MQTT.

  Durante o desenvolvimento, funcionalidades de depuração permaneceram
  ativas no equipamento. Antes da implantação comercial, a equipe de
  segurança solicitou uma avaliação técnica.

  ┌─────────────────────────────────────────────────────────────┐
  │  METODOLOGIA                                                │
  │  OWASP IoT Security Testing Guide (ISTG) — 8 etapas        │
  │                                                             │
  │  1. Reconhecimento do dispositivo                           │
  │  2. Preservação e identificação do firmware                 │
  │  3. Análise estática do firmware                            │
  │  4. Análise das interfaces físicas (UART, JTAG, SPI)        │
  │  5. Análise da comunicação de rede (MQTT)                   │
  │  6. Demonstração controlada de fragilidades                 │
  │  7. Mapeamento e classificação de riscos                    │
  │  8. Plano de hardening para versão comercial                │
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │  PRINCIPAIS ACHADOS                                         │
  │                                                             │
  │  [ALTO]  F01 — UART exposta com credenciais no log de boot  │
  │  [ALTO]  F02 — Flash sem criptografia (extraível)           │
  │  [ALTO]  F03 — MQTT sem TLS (porta 1883 plaintext)          │
  │  [ALTO]  F04 — Credenciais Wi-Fi hardcoded no firmware      │
  │  [ALTO]  F05 — OTA via HTTP sem verificação de assinatura   │
  │  [ALTO]  F06 — Broker MQTT sem autenticação / ACL           │
  │  [MÉDIO] F07 — JTAG habilitado e acessível fisicamente      │
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │  REFERÊNCIAS                                                │
  │  • OWASP IoT Security Testing Guide (ISTG)                  │
  │  • NIST IR 8259A — IoT Cybersecurity Baseline               │
  │  • ETSI EN 303 645 v3.1.3 — Consumer IoT Security          │
  │  • MITRE EMB3D — Embedded Device Threat Model               │
  │  • Espressif ESP-IDF Security Documentation                 │
  └─────────────────────────────────────────────────────────────┘

  Disciplina : Hardware Hacking IoT — UniFeCAF
  Data       : 30 de setembro de 2026
"""

print(texto)
