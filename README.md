# Whisper Streaming for Wowza Streaming Engine

This provides a docker container to run a Whisper services that integrates with WSE module *********
It can also run standalone and pull in an RTMP stream using ffmpeg 

## Usage

### Dockerfile

Dockerfile to build a phyton application using OpenAI Whisper that listens on a port that recieves raw audio and returns JSON for detected speach that gets integrate with the video feed as webVTT

### local_build.sh

Builds the docker container with the tag `whisper_streaming:local`

### local_run.sh

Runs the whipser server with a set of variables.

### docker-compose.yaml

A docker compose file that includes the WSE and WSEM and runs Whisper


### Docker Environment Variables

|Variable  |Default  |Description |
|----------|---------|------------|
|BACKEND   |faster-whisper| [faster-whisper,whisper_timestamped,openai-api] Load only this backend for Whisper processing.|
|MODEL     |  tiny.en| [tiny.en,tiny,base.en,base,small.en,small,medium.en,medium,large-v1,large-v2,large-v3,large,large-v3-turbo] Name size of the Whisper model to use. The model is automatically downloaded from the model hub if not present in model cache dir. (/tmp)|
|LANGUAGE  |     auto| Source language code, e.g. en,de,cs, or 'auto' for language detection.|
|LOG_LEVEL |     INFO| [DEBUG,INFO,WARNING,ERROR,CRITICAL] The level for logging|
|SOURCE_STREAM | none| an RTMP url to pull a stream in.  Uses ffmpeg to capture the auto and forwards the raw audio to the service |
|MIN_CHUNK_SIZE | 1| Minimum audio chunk size in seconds. It waits up to this time to do processing. If the processing takes shorter time, it waits, otherwise it processes the whole segment that was received by this time.|
|SAMPLING_RATE | 16000| Sample rate of the Audio.  |
|REPORT_LANGUAGE | none| Language to report back to WSE|


### JSON

The service returns a json object in the format
```json
{
    "language": "en",
    "start": "7.580",
    "end": "8.540",
    "text": "this is text from whisper"
}
```

### GPU

This container and Whisper does support NVIDIA GPU for increased performance with larger models.  Run the docker container with `--gpus all`
 and `-e FP16=true` along with adding `torch` and `triton` python libraries in the Dockerfile.

## Acknowledgments

This project builds upon the work from:
- [Whisper Streaming](https://github.com/ufal/whisper_streaming)
- [OpenAI Whisper](https://github.com/openai/whisper)

[Original README.md](https://github.com/WowzaMediaSystems/whisper_streaming/blob/main/README_ORG.md)

## Contact

[Wowza Media Systems, LLC](https://www.wowza.com/contact)

## License

This code is distributed under the [Wowza Public License](https://github.com/WowzaMediaSystems/whisper_streaming/blob/main/LICENSE.txt).
