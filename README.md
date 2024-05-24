# SMART_Backend_App
SMART Flask backend app that retrieves observation lab reports from EPIC and sends an email if abnormal lab reports are found using a cron job every 24 hours.

## Setup && Running the app

Clone the repository
```
git clone https://github.com/Bijitakc/SMART_Backend_App.git
```

Copy the environment variables template in env_template.txt to a new file .env.dev and add your own variables.

Add your keys to a keys.json file containing the private keys used with epic app's public key

Build and run docker compose
```
docker compose --env-file .env.dev -f docker-compose-dev.yml build
docker compose --env-file .env.dev -f docker-compose-dev.yml up -d
```
