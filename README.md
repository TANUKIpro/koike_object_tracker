## イメージのビルド
```
export DOCKER_BUILDKIT=1
# 1) base
docker build -f docker/base.Dockerfile -t base-py310:latest .

# 2) sensor
docker build -f docker/sensor.Dockerfile -t sensor:latest .

# 3) perception
docker build -f docker/perception.Dockerfile -t perception:latest .
```

# 動作確認
1. コンテナの起動前準備
```
# X表示許可
xhost +local:docker || xhost +local:root

# XAUTHORITY と X11_DIR を環境に
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
export X11_DIR=/tmp/.X11-unix
```

2. コンテナの起動
```
# 起動（バックグラウンド）
docker compose up -d ros2-xtion perception

# それぞれ入る
docker compose exec perception bash
```

### カメラ起動・接続の確認(ros2-xtion)
```
# トピックの起動確認
(ホストPC) docker compose exec ros2-xtion bash -lc 'source /opt/ros/humble/setup.bash && ros2 topic list'

# コンテナ内に入ってrqtを立ち上げ
(ホストPC) docker compose exec ros2-xtion bash
(コンテナ) rqt
```

### SAM2の動作確認(perception)
```
# コンテナ内に入ってモデルのDLとサンプル実行
(ホストPC) docker compose exec perception bash
(コンテナ) /usr/bin/python3.10 scripts/get_model.py

# SAM2デモ動画のトラッキング
(コンテナ) /usr/bin/python3.10 scripts/sam2_test.py

# ros2-xtionからデータ取得し表示
(コンテナ) source /opt/ros/humble/setup.bash
(コンテナ) /usr/bin/python3.10 scripts/show_rgb.py
```
