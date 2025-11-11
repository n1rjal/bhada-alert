# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Create a non-root user
RUN useradd --create-home appuser
USER appuser

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy the rest of the application's code
COPY --chown=appuser:appuser src/ ./src

# Define the command to run your app
CMD ["/bin/bash", "-c", "cd src && python -m property_monitor"]
