# Whisper Streaming for Wowza Streaming Engine

This provides a docker container to run a Whisper service that integrates with the Wowza Streaming Engine module [wse-plugin-caption-handlers](https://github.com/WowzaMediaSystems/wse-plugin-caption-handlers)
It can also run in standalone mode and pull in an RTMP stream using ffmpeg 

## Usage

### Files

##### Dockerfile

> Dockerfile to build a phyton application using OpenAI Whisper that listens on a port that recieves raw audio and returns JSON for detected speach that gets integrate with the video feed as WebVTT or Embedded 608/708.

##### local_build.sh

>Builds the docker container with the tag `whisper_streaming:local`

##### local_run.sh

> Runs the whipser server docker container with a set of variables.

##### docker-compose.yaml

> A docker compose file that includes Wowza Streaming Engine, Wowza Streaming Engine Manager and runs Whisper.


### Environment Variables

|Variable  |Default  |Description |
|:---------|--------:|:-----------|
|BACKEND   |faster-whisper| [faster-whisper,whisper_timestamped,openai-api] Load only this backend for Whisper processing.|
|MODEL     |  tiny.en| [tiny.en,tiny,base.en,base,small.en,small,medium.en,medium,large-v1,large-v2,large-v3,large,large-v3-turbo] Name size of the Whisper model to use. The model is automatically downloaded from the model hub if not present in model cache dir. (/tmp)|
|USE_GPU   | Flase | Use the GPU if available and installed |
|LANGUAGE  |     auto| Source language code, e.g. en,de,cs, or 'auto' for language detection.|
|LOG_LEVEL |     INFO| [DEBUG,INFO,WARNING,ERROR,CRITICAL] The level for logging|
|SOURCE_STREAM | none| an RTMP url to pull a stream in.  Uses ffmpeg to capture audio and forwards the raw audio to the service |
|MIN_CHUNK_SIZE | 1| Minimum audio chunk size in seconds. It waits up to this time to do processing. If the processing takes shorter time, it waits, otherwise it processes the whole segment that was received by this time.|
|SAMPLING_RATE | 16000| Sample rate of the Audio.  |
|REPORT_LANGUAGE | none| Language to report back to WSE|

### JSON

The service returns a json object in the format to the websocket
```json
{
    "language": "en",
    "start": "7.580",
    "end": "8.540",
    "text": "this is text from whisper"
}
```

### TEST

```
ffmpeg -hide_banner -loglevel error -f flv -i rtmp://localhost/live/myStream -c:a pcm_s16le -ac 1 -ar 16000 -f s16le - | nc localhost 3000
```
```
ffmpeg -hide_banner -loglevel error -re -i <video_file.mp4> -c:a pcm_s16le -ac 1 -ar 16000 -f s16le - | nc localhost 3000
```
### GPU

This container and Whisper does support NVIDIA GPU for increased performance with larger models:  
1. Install `torch` and `triton` python libraries in the Dockerfile.
2. Install `cudnn9-cuda-12` package in the Dockerfile.
3. Run the docker container with `--gpus all`
4. Run the docker container with environment variables `-e USE_GPU=True` and `-e FP16=true`

## Acknowledgments

This project builds upon the work from:

- [Whisper Streaming](https://github.com/ufal/whisper_streaming)
- [OpenAI Whisper](https://github.com/openai/whisper)

[Original README.md](https://github.com/WowzaMediaSystems/whisper_streaming/blob/main/README_ORG.md)

## Contact

[Wowza Media Systems, LLC](https://www.wowza.com/contact)

## License

This code is distributed under the [Wowza Public License](https://github.com/WowzaMediaSystems/whisper_streaming/blob/main/LICENSE.txt).
