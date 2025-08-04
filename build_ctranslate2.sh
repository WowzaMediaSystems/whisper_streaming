#!/bin/bash

#buld the lib and whl files
docker build -t ctranslate2:latest -f Dockerfile.ctranslate2 .
if [ $? -eq 0 ]; then
	#copies build artifacts 
	docker run -it -v ./CTranslate2:/tmp ctranslate2:latest
	echo "Files copied to ./CTranslate2"
fi