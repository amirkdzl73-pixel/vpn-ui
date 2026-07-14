#!/bin/bash
set -e

export VPNUI_DB_FOLDER=/data

exec /app/vpn-ui --port ${PORT:-8080}
