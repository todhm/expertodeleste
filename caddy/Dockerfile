FROM caddy:2.4.6-alpine
COPY Caddyfile /etc/caddy/Caddyfile
RUN mkdir -p /etc/caddy/conf.d
RUN mkdir -p /var/www/apiserver
RUN mkdir -p /var/www/www
RUN mkdir -p /var/log/caddy

COPY apiserver.html /var/www/apiserver/index.html
COPY www.html /var/www/www/index.html

COPY apiserver.conf /etc/caddy/conf.d/apiserver.conf
COPY www.conf /etc/caddy/conf.d/www.conf
