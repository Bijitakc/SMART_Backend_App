FROM python:3.9

# Create and change to the app directory.
WORKDIR /app

# Copy the requirements.txt file to the container.
COPY requirements.txt /app/requirements.txt

# Install dependencies.
RUN pip install -r requirements.txt

# Copy the rest of the app to the container.
COPY . /app

# Give permission to run the script
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "3", "core.wsgi:app", "--reload"]