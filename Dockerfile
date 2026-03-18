# Use the official Python 3.11 image
FROM python:3.11.7-slim

# Set the working directory to /app
WORKDIR /app

# Set environment variables for Hugging Face Spaces
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Create a non-root user that Hugging Face Spaces requires (UID 1000)
RUN useradd -m -u 1000 user

# Install necessary system dependencies if any are needed for PDF/Image processing
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/*

# Switch to the non-root user
USER user

# Set the working directory to the user's home
WORKDIR $HOME/app

# Copy the requirements file into the container
COPY --chown=user requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the rest of the application code into the container
COPY --chown=user . .

# Expose port 7860 (Hugging Face Default)
EXPOSE 7860

# Run the FastAPI server via uvicorn
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
