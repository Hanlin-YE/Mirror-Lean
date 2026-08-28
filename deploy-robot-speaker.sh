#!/usr/bin/env bash
# Deploy robot-speaker-server.py (and the Unitree stock-TTS helper) to the G1 robot.
set -e

ROBOT_IP=${ROBOT_IP:-192.168.52.241}
ROBOT_USER=${ROBOT_USER:-unitree}
ROBOT_PASS=${ROBOT_PASS:-123}
REMOTE_DIR="/home/${ROBOT_USER}/robot-speaker"

ssh_with_pass() {
    sshpass -p "${ROBOT_PASS}" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$@"
}

scp_with_pass() {
    sshpass -p "${ROBOT_PASS}" scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$@"
}

echo "==> Creating remote directory ${REMOTE_DIR} on ${ROBOT_IP}"
ssh_with_pass "${ROBOT_USER}@${ROBOT_IP}" "mkdir -p ${REMOTE_DIR}"

echo "==> Copying server + TTS helper source"
scp_with_pass robot-speaker-server.py robot-tts.cc CMakeLists.txt "${ROBOT_USER}@${ROBOT_IP}:${REMOTE_DIR}/"

echo "==> Building TTS helper on robot"
ssh_with_pass "${ROBOT_USER}@${ROBOT_IP}" "cd ${REMOTE_DIR} && rm -rf build && mkdir build && cd build && cmake .. && make -j\$(nproc)"

echo "==> Stopping old server"
ssh_with_pass "${ROBOT_USER}@${ROBOT_IP}" "pkill -f robot-speaker-server.py || true"

echo "==> Starting new server"
ssh_with_pass "${ROBOT_USER}@${ROBOT_IP}" "cd ${REMOTE_DIR} && nohup python3 robot-speaker-server.py > /tmp/robot-speaker.log 2>&1 &"

echo "==> Done. View logs with:"
echo "    ssh ${ROBOT_USER}@${ROBOT_IP} 'tail -f /tmp/robot-speaker.log'"
