# Forta exporter

## Requirements

- python 3.10.x

## Installation

```
cd ~
git clone https://github.com/P-OPSTeam/forta-exporter.git
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.10 python3-virtualenv python3.10-distutils
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10
cd forta-exporter
virtualenv -p /usr/bin/python3.10 .venv
pip install -r requirements.txt
```

## Run it

```
export SCANNER_ADDRESS=<fill up your scanner_address>
python3.10 exporter.py
```

## As a service

```
export SCANNER_ADDRESS=<fill up your scanner_address>
sed "s/<scanner_address>/${SCANNER_ADDRESS}/g" forta-exporter.service
sudo cp forta-exporter.service /etc/systemd/system/
sudo systemctl enable forta-exporter 
sudo systemctl start forta-exporter
```
