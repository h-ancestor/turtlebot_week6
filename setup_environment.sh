#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL="$ROOT/models/gesture_recognizer.task"
URL='https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task'
if [[ ! -f "$MODEL" ]]; then
  echo 'Downloading the official MediaPipe Gesture Recognizer model...'
  curl -fL "$URL" -o "$MODEL"
fi
sudo apt update
sudo apt install -y curl python3-pip python3-opencv python3-numpy python3-pil
python3 -m pip install --user --requirement "$ROOT/requirements.txt"
echo 'Dependencies and model are ready.'
echo 'Next: from the workspace root run colcon --log-base log build --base-paths "thực _ hành _06/gesture_turtlebot4" --symlink-install'
