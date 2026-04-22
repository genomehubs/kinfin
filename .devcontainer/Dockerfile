# Start with Node.js 20 LTS which includes npm
FROM node:20-bookworm

# Install Python 3.11 and other system dependencies required by the project
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    git \
    curl \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a symbolic link for python3 to python3.11
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Create a non-root user for container operations (improves sandboxing)
RUN useradd -m -s /bin/bash devuser && \
    mkdir -p /workspace && \
    chown -R devuser:devuser /workspace

# Set working directory
WORKDIR /workspace

# Set environment variables for Python and npm
ENV PYTHONUNBUFFERED=1 \
    PATH="/home/devuser/.local/bin:${PATH}" \
    PIP_BREAK_SYSTEM_PACKAGES=1

# Install pip packages (as root, before switching user)
RUN python -m pip install --upgrade pip setuptools wheel && \
    chown -R devuser:devuser /home/devuser

# Switch to non-root user
USER devuser
