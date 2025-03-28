FROM sudilav1/xmarte:main

# Create a new user and set up a home directory
RUN useradd -m -s /bin/bash martecompilerrunner

RUN pip install httpx starlette uvicorn pyftpdlib pyyaml martepy

RUN mkdir /opt/martecompiler

COPY settings.yml /opt/martecompiler/settings.yml

RUN chmod -R 777 /home/martecompilerrunner

RUN mkdir -p /opt/martecompiler/martecompiler

# Set the new user as the default
USER martecompilerrunner

# Set the working directory to the new user's home
WORKDIR /home/martecompilerrunner
