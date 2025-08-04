#!/bin/bash

docker build -t ctranslate2:latest -f Dockerfile.ctranslate2 .
docker run -it -v ./CTranslate2:/tmp ctranslate2:latest