#!/bin/bash

# Colori per i messaggi
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}>>> Inizio installazione xOS...${NC}"

# 1. Controllo permessi root
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}Per favore, esegui lo script come root (usa sudo ./setup.sh)${NC}"
  exit
fi

# 2. Controllo e installazione Python 3
echo -e "${GREEN}>>> Controllo Python 3...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 non trovato. Installazione in corso...${NC}"
    apt update && apt install -y python3 python3-pip python3-venv
else
    echo -e "${GREEN}Python 3 è già installato.${NC}"
fi

# 3. Creazione Ambiente Virtuale e installazione librerie
echo -e "${GREEN}>>> Configurazione ambiente Python...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

./venv/bin/pip install --upgrade pip
./venv/bin/pip install flask psutil

# 4. Configurazione Avvio Automatico (Systemd)
echo -e "${GREEN}>>> Configurazione avvio automatico...${NC}"

# Ottieni il percorso assoluto della cartella corrente
APP_PATH=$(pwd)
USER_NAME=$(logname)

# Creazione del file .service
cat <<EOF > /etc/systemd/system/xos.service
[Unit]
Description=xOS Centrale Service
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$APP_PATH
ExecStart=$APP_PATH/venv/bin/python3 $APP_PATH/casaos.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Attivazione del servizio
systemctl daemon-reload
systemctl enable xos.service
systemctl start xos.service

echo -e "${GREEN}--------------------------------------------------${NC}"
echo -e "${GREEN}INSTALLAZIONE COMPLETATA!${NC}"
echo -e "xOS è ora attivo e si avvierà da solo col PC."
echo -e "Puoi vedere il sito su: http://localhost:8080"
echo -e "Registro attività creato in: $APP_PATH/activity.log"
echo -e "${GREEN}--------------------------------------------------${NC}"