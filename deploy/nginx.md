# Настройка Nginx на сервере

Nginx принимает HTTPS-запросы Telegram и передаёт их боту, который слушает `127.0.0.1:8085`.
Конфиг — [nginx.conf](nginx.conf). Команды ниже рассчитаны на Debian/Ubuntu и выполняются на сервере.

## Что должно быть готово

- A-запись домена указывает на IP сервера.
- Порты 80 и 443 открыты снаружи (например, `sudo ufw allow 80,443/tcp`).
- Репозиторий лежит на сервере, бот запущен через `docker compose up -d --build`.
- Установлены Nginx и certbot:

  ```sh
  sudo apt install nginx certbot python3-certbot-nginx
  ```

Во всех командах используется переменная с доменом — задайте её один раз:

```sh
DOMAIN=bot.example.com   # ваш домен, без https://
```

## 1. Получить сертификат

Сертификат выпускается **до** подключения конфига: конфиг ссылается на файлы сертификата, и без
них Nginx не запустится.

```sh
sudo certbot certonly --nginx -d "$DOMAIN" --deploy-hook "systemctl reload nginx"
```

Важно именно `certonly`: в этом режиме certbot только выпускает сертификат и не трогает конфиги
Nginx. `--deploy-hook` перезагружает Nginx после каждого автопродления, чтобы он подхватил новый
сертификат.

Файлы появятся в `/etc/letsencrypt/live/$DOMAIN/`.

## 2. Установить конфиг

Из корня репозитория:

```sh
sudo cp deploy/nginx.conf /etc/nginx/sites-available/chatroullete.conf
sudo sed -i "s/bot\.example\.com/$DOMAIN/g" /etc/nginx/sites-available/chatroullete.conf
```

Если меняли `WEBHOOK_PATH` или `BOT_PORT` в `.env`, поправьте в конфиге `location = /webhook` и
порт в блоке `upstream`.

## 3. Подключить и перезагрузить

```sh
sudo ln -s /etc/nginx/sites-available/chatroullete.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Путь в `ln -s` должен быть абсолютным, иначе ссылка окажется битой.

## 4. Указать адрес боту

В `.env` бота:

```
WEBHOOK_BASE_URL=https://bot.example.com
```

После изменения перезапустите бота — при старте он сам регистрирует webhook в Telegram:

```sh
docker compose up -d bot
```

## 5. Проверить

```sh
curl -i "https://$DOMAIN/"          # 404 — отвечает наш конфиг
curl -i "https://$DOMAIN/webhook"   # 403 — запрос не из сетей Telegram
```

Состояние webhook со стороны Telegram (подставьте токен бота):

```sh
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

В ответе `url` должен совпадать с `WEBHOOK_BASE_URL + WEBHOOK_PATH`, а поля `last_error_message`
быть не должно. Затем отправьте боту `/start`.

## Если что-то не работает

| Симптом | Причина и решение |
| --- | --- |
| `nginx -t`: `cannot load certificate` | Сертификат не выпущен или в конфиге другой домен. Проверьте `ls /etc/letsencrypt/live/`. |
| `nginx -t`: `conflicting server name` | Домен описан ещё в одном файле, обычно в `sites-enabled/default`. Удалите оттуда блоки `server` с этим доменом. |
| Открывается стандартная страница Nginx | Конфиг не подключён: нет ссылки в `sites-enabled` или Nginx не перезагружен. |
| `getWebhookInfo`: `Wrong response from the webhook: 502 Bad Gateway` | Бот не запущен или слушает другой порт. Проверьте `docker compose ps` и `BOT_PORT`. |
| `getWebhookInfo`: `403 Forbidden` | Перед Nginx стоит CDN или другой прокси, и запрос приходит не с адресов Telegram. Уберите из конфига строки `allow` и `deny`. |
| `getWebhookInfo`: `401 Unauthorized` | Telegram шлёт старый `WEBHOOK_SECRET`. Перезапустите бота, чтобы он заново зарегистрировал webhook. |
| `getWebhookInfo`: ошибка SSL | В `ssl_certificate` должен быть `fullchain.pem`, а не `cert.pem`. |

### Certbot записал сертификат в `default`

Так бывает, если запустить `certbot --nginx` (без `certonly`) до подключения конфига: certbot не
находит блок с нужным доменом и создаёт свой в `/etc/nginx/sites-enabled/default`. Сертификат при
этом выпущен нормально, нужно только убрать лишнее:

1. Найдите, что дописал certbot:

   ```sh
   grep -n "$DOMAIN\|managed by Certbot" /etc/nginx/sites-enabled/default
   ```

2. Удалите из `default` блоки `server` с этим доменом (обычно их два: с `listen 443 ssl` и с
   редиректом с 80 порта). Если в `default` только стандартная заглушка, проще отключить его:
   `sudo rm /etc/nginx/sites-enabled/default`.
3. Убедитесь, что в `chatroullete.conf` есть строки `ssl_certificate` и `ssl_certificate_key` с
   путями из `/etc/letsencrypt/live/$DOMAIN/`, и выполните шаг 3.
