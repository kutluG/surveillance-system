# Edge AI Service Dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libssl-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY edge_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create models directory and download face detection models
RUN mkdir -p /app/models

# Download OpenCV face detection models
RUN python -c "\
import cv2; \
import urllib.request; \
import os; \
haar_url = 'https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml'; \
haar_path = '/app/models/haarcascade_frontalface_default.xml'; \
urllib.request.urlretrieve(haar_url, haar_path); \
try: \
    prototxt_url = 'https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/opencv_face_detector.pbtxt'; \
    model_url = 'https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/opencv_face_detector_uint8.pb'; \
    prototxt_path = '/app/models/opencv_face_detector.pbtxt'; \
    model_path = '/app/models/opencv_face_detector_uint8.pb'; \
    urllib.request.urlretrieve(prototxt_url, prototxt_path); \
    urllib.request.urlretrieve(model_url, model_path); \
    print('DNN models downloaded successfully'); \
except Exception as e: \
    print(f'DNN model download failed: {e}'); \
    print('Will use Haar cascade only'); \
"

# Copy code
COPY shared/ /app/shared/
COPY edge_service/ .

# Set environment variables for face anonymization
ENV PYTHONUNBUFFERED=1
ENV ANONYMIZATION_ENABLED=true
ENV PRIVACY_LEVEL=moderate
ENV ANONYMIZATION_METHOD=blur
ENV FACE_MODEL_PATH=/app/models
ENV HAAR_CASCADE_PATH=/app/models/haarcascade_frontalface_default.xml
ENV DNN_PROTOTXT_PATH=/app/models/opencv_face_detector.pbtxt
ENV DNN_MODEL_PATH=/app/models/opencv_face_detector_uint8.pb

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]