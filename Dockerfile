# use an official Python runtime as a parent image
FROM python:3.12

# set the working directory in the container
WORKDIR /app

# copy the requirements file first to leverage Docker cache
COPY requirements.txt /app/requirements.txt

# install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# copy the rest of the application code
COPY app /app

# make port 80 available to the world outside this container
EXPOSE 80

# run main.py when the container launches
CMD ["python", "main.py"]   