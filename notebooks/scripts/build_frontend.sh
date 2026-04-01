#!/usr/bin/env bash
# Rebuild the phone dashboard Vue SPA.
set +e
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
cd /home/boxbunny/Desktop/doomsday_integration/boxing_robot_ws/src/boxbunny_dashboard/frontend
npm run build 2>&1
