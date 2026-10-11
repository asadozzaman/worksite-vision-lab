# Build checkpoint-inspector.Dockerfile with this tag first.
FROM worksite-checkpoint-inspector:8.4.173
USER root
RUN pip install --no-cache-dir lap==0.5.12 pydantic==2.13.4 pytest==9.0.3
ENV YOLO_AUTOINSTALL=false
USER 65534:65534
