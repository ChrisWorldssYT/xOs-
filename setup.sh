#!/bin/bash

# Colori per il terminale
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' 

echo -e "${GREEN}--------------------------------------------------${NC}"
echo -e "${GREEN}    Inizio Installazione xOS - Cloud System       ${NC}"
echo -e "${GREEN}--------------------------------------------------${NC}"

# 1. Controllo permessi root
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}Errore: Devi eseguire lo script con sudo! (sudo ./setup.sh)${NC}"
  exit
fi

# 2. Variabili di percorso
# Lo script rileva l'utente che ha lanciato il sudo per trovare la sua home
REAL_USER=$(logname)
USER_HOME=$(eval echo ~$REAL_USER)
APP_PATH="$USER_HOME/xOs-"

echo -e "${GREEN}>>> Cartella di installazione: $APP_PATH${NC}"

# 3. Installazione dipendenze
echo -e "${GREEN}[1/4] Aggiornamento sistema e Python...${NC}"
apt update -y
apt install -y python3 python3-pip python3-venv

# 4. Setup Ambiente Virtuale
echo -e "${GREEN}[2/4] Creazione ambiente virtuale e librerie...${NC}"
cd "$APP_PATH" || { echo -e "${RED}Errore: Cartella $APP_PATH non trovata!${NC}"; exit 1; }

rm -rf venv
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install flask psutil

# Fix permessi per l'utente
chown -R $REAL_USER:$REAL_USER "$APP_PATH"

# 5. Configurazione Avvio Automatico (Systemd)
echo -e "${GREEN}[3/4] Configurazione servizio di sistema...${NC}"

cat <<EOF > /etc/systemd/system/xos.service
[Unit]
Description=xOS Centrale Service
After=network.target

[Service]
User=$REAL_USER
WorkingDirectory=$APP_PATH
ExecStart=$APP_PATH/venv/bin/python3 $APP_PATH/casaos.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 6. Attivazione Finale
echo -e "${GREEN}[4/4] Avvio xOS...${NC}"
systemctl daemon-reload
systemctl enable xos.service
systemctl start xos.service

echo -e "${GREEN}--------------------------------------------------${NC}"
echo -e "${GREEN}INSTALLAZIONE COMPLETATA!${NC}"
echo -e "xOS è ora un servizio di sistema attivo."
echo -e "Percorso eseguibile: $APP_PATH/casaos.py"
echo -e "URL Locale: http://localhost:8080"
echo -e "${GREEN}--------------------------------------------------${NC}"