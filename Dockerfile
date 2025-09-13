FROM python:3.10-slim
LABEL version="01.00.044" description="Rebeca Agent with updated Gemini configuration and Slack token handling"

WORKDIR /app

# Copiar solo los archivos necesarios
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de los archivos
COPY . .

# Asegurar que el directorio de trabajo sea correcto
WORKDIR /app

CMD ["python", "main.py"]