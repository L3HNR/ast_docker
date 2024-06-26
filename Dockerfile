FROM nvidia/cuda:11.6.2-cudnn8-runtime-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    git \
    python3.9 \
    python3.9-dev \
    python3.9-distutils \
    python3-pip \
    wget \
    sox \
    libsox-dev \
    git-lfs \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.9 as default
RUN ln -sf /usr/bin/python3.9 /usr/bin/python

# Install pip and upgrade it
RUN python -m pip install --upgrade pip

# Create a working directory
WORKDIR /app

# Clone the AST repository
RUN git clone https://github.com/Arashi0987/ast.git

# Change the torchvision version in requirements.txt
WORKDIR /app/ast

# Install Python dependencies
RUN pip install -r requirements.txt
RUN pip install gradio

# Set the entrypoint
CMD ["python", "webui.py"]

