FROM python:3.10
WORKDIR /chatbot
COPY ./requirements.txt /chatbot/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /chatbot/requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
