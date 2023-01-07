FROM gcc:latest

RUN apt update && apt install -y git python3-pip ffmpeg

RUN git clone https://github.com/ggerganov/whisper.cpp

WORKDIR /whisper.cpp

RUN make && chmod +x ./main

# Copy large model
COPY models/ggml-large.bin models/ggml-large.bin

# Install python dependencies
COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt