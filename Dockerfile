FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set working directory
WORKDIR /app

# Install Python dependencies first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chrome browser (not chromium, as the code uses channel='chrome')
RUN playwright install chrome

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/news data/articles data/images

# Set environment variables
ENV PYTHONUNBUFFERED=1

# HuggingFace Spaces uses port 7860 by default
EXPOSE 7860

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
