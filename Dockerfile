# Use the official Python 3.11 image
FROM python:3.11.7-slim

# Set the working directory to /app
WORKDIR /app

# Set environment variables for Hugging Face Spaces
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Create a non-root user that Hugging Face Spaces requires (UID 1000)
RUN useradd -m -u 1000 user

# Install necessary system dependencies, Node.js 20, and Curl for Caddy
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libpoppler-cpp-dev \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Switch to the non-root user
USER user

# Set the working directory to the user's home
WORKDIR $HOME/app

# Download Caddy binary to the root of our app
RUN curl -L "https://caddyserver.com/api/download?os=linux&arch=amd64" -o caddy && chmod +x caddy

# Copy backend requirements first for caching
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy frontend packages for caching
COPY --chown=user frontend/package*.json ./frontend/
RUN cd frontend && npm install

# Copy the rest of the application
COPY --chown=user . .

# Build the Next.js frontend into a production package!
RUN cd frontend && npm run build

# Make sure our startup script is executable
RUN chmod +x start.sh

# Expose port 7860 (Hugging Face Default)
EXPOSE 7860

# Run our unified start script that boots Caddy, Python, and Node
CMD ["./start.sh"]
