## イメージのビルド  (Build the image)
```
export DOCKER_BUILDKIT=1
# 1) base
docker build -f docker/base.Dockerfile -t base-py310:latest .

# 2) sensor
docker build -f docker/sensor.Dockerfile -t sensor:latest .

# 3) perception
docker build -f docker/perception.Dockerfile -t perception:latest .
```

# 動作確認 (Operation instructions)
1. コンテナの起動前準備 (Preparation)
```
# X表示許可 (Xhost permissions)
xhost +local:docker || xhost +local:root

# XAUTHORITY と X11_DIR を環境に (Setting XAUTHORITY and X11_DIR in the environment)
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
export X11_DIR=/tmp/.X11-unix
```

2. コンテナの起動 (Start the container)
```
# 起動（バックグラウンド） (Start [Background])
docker compose up -d ros2-xtion perception

# それぞれ入る
docker compose exec perception bash
```

### カメラ起動・接続の確認(ros2-xtion) (Camera startup and connection check [ros2-xtion])
```
# トピックの起動確認 (Check topic startup)
(ホストPC) [host PC] docker compose exec ros2-xtion bash -lc 'source /opt/ros/humble/setup.bash && ros2 topic list'

# コンテナ内に入ってrqtを立ち上げ (Enter the container and launch rqt)
(ホストPC) [host PC] docker compose exec ros2-xtion bash
(コンテナ) [container] rqt
```

### SAM2の動作確認(perception) (Check SAM2 operation[perception])
```
# コンテナ内に入ってモデルのDLとサンプル実行 (Enter the container and download the model and run the sample)
(ホストPC) [host PC] docker compose exec perception bash
(コンテナ) [container] /usr/bin/python3.10 scripts/get_model.py

# SAM2デモ動画のトラッキング (View SAM2 video tracking demo)
(コンテナ) [container] /usr/bin/python3.10 scripts/sam2_test.py

# ros2-xtionからデータ取得し表示 (Obtain and display data from ros2-xtion)
(コンテナ) [container] source /opt/ros/humble/setup.bash
(コンテナ) [container] /usr/bin/python3.10 scripts/show_rgb.py
```
