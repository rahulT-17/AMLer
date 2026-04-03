
# step 1: build the application
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# copy the rest of the application code
COPY . .    

RUN sed -i 's/\r$//' start-api.sh
RUN chmod +x start-api.sh

EXPOSE 8000

CMD ["./start-api.sh"]