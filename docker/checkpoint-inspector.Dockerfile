FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir torch==2.7.0 torchvision==0.22.0 \
    --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir ultralytics==8.4.173 numpy==1.26.4 opencv-python==4.11.0.86
ENV YOLO_CONFIG_DIR=/tmp/yolo MPLCONFIGDIR=/tmp/matplotlib HOME=/tmp
USER 65534:65534
WORKDIR /tmp
ENTRYPOINT ["python"]
