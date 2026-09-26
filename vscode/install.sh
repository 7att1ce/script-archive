#!/usr/bin/env bash

set -euxo pipefail

ROOT_DIR="/home/user/portable-apps"
VSCODE_LINK="https://code.visualstudio.com/sha/download?build=stable&os=linux-x64"

wget ${VSCODE_LINK} -O "${ROOT_DIR}/vscode.tar.gz"
tar -xvzf "${ROOT_DIR}/vscode.tar.gz" -C ${ROOT_DIR}
mv "${ROOT_DIR}/VSCode-linux-x64" "${ROOT_DIR}/vscode"
mkdir -p "${ROOT_DIR}/vscode/data/tmp"
sudo chown root "${ROOT_DIR}/vscode/chrome-sandbox"
sudo chmod 4755 "${ROOT_DIR}/vscode/chrome-sandbox"
