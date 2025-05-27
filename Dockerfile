# Imagen base oficial de Python
FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos al contenedor
COPY . .

# Instala las dependencias
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expone el puerto en el que se ejecutará la app
EXPOSE 8000

# Comando para iniciar la app con gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
