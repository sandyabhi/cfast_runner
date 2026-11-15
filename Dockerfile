FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    make \
    gfortran \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*


# --------------------------------
# Build CFAST
# --------------------------------

WORKDIR /opt

RUN git clone --depth 1 --branch CFAST-7.7.7 \
    https://github.com/firemodels/cfast.git

WORKDIR /opt/cfast/Build/CFAST/gnu_linux

RUN chmod +x make_cfast.sh && \
    ./make_cfast.sh

RUN cp cfast7_linux /usr/local/bin/cfast && \
    chmod +x /usr/local/bin/cfast


# --------------------------------
# Install Web Application
# --------------------------------

WORKDIR /app

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY main.py .


# --------------------------------
# Start FastAPI
# --------------------------------

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
