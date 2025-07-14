##
## This code and all components (c) Copyright 2006 - 2025, Wowza Media Systems, LLC. All rights reserved.
## This code is licensed pursuant to the Wowza Public License version 1.0, available at www.wowza.com/legal.
##
FROM python:3.12-bookworm

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install ffmpeg netcat-traditional -y

RUN pip install --no-deps openai-whisper
# dependancies
RUN pip install numba numpy tqdm more-itertools tiktoken

# Install these for GPU, increases image size by ~5GB
# RUN pip install torch 
# RUN pip install "triton>=2.0.0; platform_machine=='x86_64' and (sys_platform=='linux' or sys_platform=='linux2')"
# RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
# RUN dpkg -i cuda-keyring_1.1-1_all.deb
# RUN apt update && apt install cudnn9-cuda-12 -y
#

RUN pip install librosa soundfile
RUN pip install faster-whisper
RUN pip install hf_xet

# create a working directory
RUN mkdir /app
WORKDIR /app

COPY *.py .
COPY samples_jfk.wav .
COPY entrypoint.sh .
COPY LICENSE.txt .

EXPOSE 3000

CMD ["/app/entrypoint.sh"]
