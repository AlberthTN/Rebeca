FROM alberth121484/base:01.00.001

# Copiar archivos de la aplicación
COPY .env .env
COPY . .

# Configurar permisos
RUN chmod +x main.py
RUN chmod 600 .env

# Comando para ejecutar la aplicación
CMD ["python", "main.py"]