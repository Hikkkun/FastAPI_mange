#!/bin/bash

# Проверка наличия docker-compose
if ! [ -x "$(command -v docker-compose)" ] && ! [ -x "$(command -v docker compose)" ]; then
  echo 'Error: docker-compose is not installed.' >&2
  exit 1
fi
# bypass.mwx.su
# Настройка переменных
domains=(bypass.mwx.su)
rsa_key_size=4096
data_path="./data/certbot"
email="" # Adding a valid address is strongly recommended
staging=0 # Set to 1 if you're testing your setup to avoid hitting request limits

# Проверка существующих данных
if [ -d "$data_path" ]; then
  echo "Found existing data for $domains at $data_path."
  read -p "Continue and replace existing certificate? (y/N) " decision
  if [ "$decision" != "Y" ] && [ "$decision" != "y" ]; then
    echo "Aborting."
    exit
  fi
fi

# Загрузка параметров TLS
if [ ! -e "$data_path/conf/options-ssl-nginx.conf" ] || [ ! -e "$data_path/conf/ssl-dhparams.pem" ]; then
  echo "### Downloading recommended TLS parameters ..."
  mkdir -p "$data_path/conf"
  if ! curl -s -o "$data_path/conf/options-ssl-nginx.conf" https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf; then
    echo "Failed to download options-ssl-nginx.conf."
    exit 1
  fi
  if ! curl -s -o "$data_path/conf/ssl-dhparams.pem" https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem; then
    echo "Failed to download ssl-dhparams.pem."
    exit 1
  fi
  echo
fi

# Создание временного сертификата
echo "### Creating dummy certificate for $domains ..."
path="/etc/letsencrypt/live/$domains"
mkdir -p "$data_path/conf/live/$domains"
if ! docker-compose run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:$rsa_key_size -days 1\
    -keyout '$path/privkey.pem' \
    -out '$path/fullchain.pem' \
    -subj '/CN=localhost'" certbot; then
  echo "Failed to create dummy certificate."
  exit 1
fi
echo

# Запуск Nginx
echo "### Starting nginx ..."
if ! docker-compose up --build -d; then
  echo "Failed to start nginx."
  exit 1
fi
echo

# Удаление временного сертификата
echo "### Deleting dummy certificate for $domains ..."
if ! docker-compose run --rm --entrypoint "\
  rm -Rf /etc/letsencrypt/live/$domains && \
  rm -Rf /etc/letsencrypt/archive/$domains && \
  rm -Rf /etc/letsencrypt/renewal/$domains.conf" certbot; then
  echo "Failed to delete dummy certificate."
  exit 1
fi
echo

# Запрос реального сертификата
echo "### Requesting Let's Encrypt certificate for $domains ..."
domain_args=""
for domain in "${domains[@]}"; do
  domain_args="$domain_args -d $domain"
done

case "$email" in
  "") email_arg="--register-unsafely-without-email" ;;
  *) email_arg="--email $email" ;;
esac

if [ $staging != "0" ]; then staging_arg="--staging"; fi

if ! docker-compose run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $staging_arg \
    $email_arg \
    $domain_args \
    --rsa-key-size $rsa_key_size \
    --agree-tos \
    --force-renewal" certbot; then
  echo "Failed to request Let's Encrypt certificate."
  exit 1
fi
echo

# Перезагрузка Nginx
echo "### Reloading nginx ..."
if ! docker-compose exec nginx nginx -s reload; then
  echo "Failed to reload nginx."
  exit 1
fi

echo "### Done."