#!/bin/sh
set -eu

if [ -z "${FRAUDLENS_PUBLIC_HOST:-}" ] ||
   [ "${#FRAUDLENS_PUBLIC_HOST}" -gt 253 ] ||
   ! printf '%s' "$FRAUDLENS_PUBLIC_HOST" | grep -Eq '^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$'; then
    echo 'FRAUDLENS_PUBLIC_HOST must be a lowercase DNS hostname' >&2
    exit 1
fi

remaining_host=$FRAUDLENS_PUBLIC_HOST
while :; do
    label=${remaining_host%%.*}
    if [ "${#label}" -gt 63 ]; then
        echo 'FRAUDLENS_PUBLIC_HOST has an oversized DNS label' >&2
        exit 1
    fi
    [ "$label" = "$remaining_host" ] && break
    remaining_host=${remaining_host#*.}
done

if [ ! -r /run/secrets/tls.crt ] || [ ! -r /run/secrets/tls.key ]; then
    echo 'readable TLS certificate and key are required' >&2
    exit 1
fi

sed "s/@@HOST@@/$FRAUDLENS_PUBLIC_HOST/g" \
    /etc/nginx/fraudlens-production.conf.template > /etc/nginx/conf.d/default.conf
sed "s/@@HOST@@/$FRAUDLENS_PUBLIC_HOST/g" \
    /etc/nginx/fraudlens-api-proxy.conf.template > /etc/nginx/fraudlens-api-proxy.conf
nginx -t
exec nginx -g 'daemon off;'
