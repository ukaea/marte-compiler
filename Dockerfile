FROM sudilav1/xmarte:main

# Create a new user and set up a home directory
RUN useradd -m -s /bin/bash martecompilerrunner
RUN useradd -m -s /bin/bash xmarterunner

RUN pip install httpx starlette uvicorn pyftpdlib pyyaml martepy

RUN mkdir /opt/martecompiler
RUN mkdir -p /opt/xmarterunner/xmarterunner

RUN chmod -R 777 /home/martecompilerrunner
RUN chmod -R 777 /home/xmarterunner

RUN mkdir -p /opt/martecompiler/martecompiler

# Set the new user as the default
USER martecompilerrunner

# Set the working directory to the new user's home
WORKDIR /home/martecompilerrunner
