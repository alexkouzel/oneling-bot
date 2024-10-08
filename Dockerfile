# Use an official Python runtime as a parent image
FROM python:3.12

# Set the working directory in the container
WORKDIR /src

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt /src/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY src /src

# Make port 80 available to the world outside this container
EXPOSE 80

# Run main.py when the container launches
CMD ["python", "main.py"]