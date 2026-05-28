# 1. Usamos una imagen base ligera de Python
FROM python:3.11-slim

# 2. Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiamos solo el archivo de requerimientos primero (buena práctica para aprovechar la caché de capas de Docker)
COPY requirements.txt .

# 4. Instalamos las dependencias sin guardar la caché de pip para mantener la imagen ligera
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiamos el resto del código fuente del proyecto
COPY . .

# 6. Comando para ejecutar la aplicación al iniciar el contenedor
CMD ["python", "main.py"]