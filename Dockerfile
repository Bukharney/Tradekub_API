FROM python:3.11.3

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .  

EXPOSE $PORT

CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload 
