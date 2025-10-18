# Use a more complete Python image that includes build tools
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# --- NEW: Install system dependencies ---
# Refresh package lists and install Graphviz and the GCC compiler
RUN apt-get update && apt-get install -y \
    build-essential \
    graphviz \
    graphviz-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Expose the port Render expects
EXPOSE 10000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]