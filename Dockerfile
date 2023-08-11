# Base image
FROM python:3.10-slim-buster

# Set the working directory
WORKDIR /app

# Copy the repository files to the container
COPY . /app


# Install dependencies using Poetry
RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install  --no-interaction --no-ansi

# Expose ports
EXPOSE 8501
EXPOSE 5000

# Set the entry point command to start the apps
CMD ["poetry", "run", "streamlit", "run", "--server.port", "8501", "app/main.py"]
