FROM golang:1.26-bookworm AS builder

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    libsqlite3-dev \
    git \
    curl \
    bash

RUN test -d third_party/Xray-core || git clone --depth 1 https://github.com/Sir-MmD/Xray-core third_party/Xray-core

RUN chmod +x build.sh

RUN CGO_ENABLED=1 ./build.sh


FROM debian:12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ca-certificates sqlite3 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/build/out/vpn-ui /app/vpn-ui

ENV VPNUI_DB_FOLDER=/data

CMD ["/app/vpn-ui"]
# railway rebuild
