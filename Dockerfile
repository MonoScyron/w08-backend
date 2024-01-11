# Use the official Python image as the base image
FROM python:3.9

# Set working directory within the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy all other files to the working directory
COPY . .

# Expose the port that Flask runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "src/app.py"]