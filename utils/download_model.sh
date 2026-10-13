#! /bin/bash

echo "Downloading YOLO26 into models directory..."
cd .. && wget -O src/pkg_2d_detection/models/yolo26n.pt https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt