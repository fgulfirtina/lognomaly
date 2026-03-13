FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıkları (SHAP derleme için)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Geçici upload dizini
RUN mkdir -p /app/temp_uploads /app/saved_models

# Modelleri build sırasında demo veriyle eğit (opsiyonel)
# RUN python train.py --demo

EXPOSE 5000

CMD ["python", "api/app.py"]
