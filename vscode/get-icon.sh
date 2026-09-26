#!/usr/bin/env bash

set -euxo pipefail

wget https://code.visualstudio.com/assets/branding/visual-studio-code-icons.zip -O /home/user/portable-apps/visual-studio-code-icons.zip
unzip /home/user/portable-apps/visual-studio-code-icons.zip -d /home/user/portable-apps
mv /home/user/portable-apps/visual-studio-code-icons/vscode.png /home/user/portable-apps/icons
