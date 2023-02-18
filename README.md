# Speech-to-text model tester

This framework is designed to make it easy for researchers and developers to evaluate the accuracy of their speech to
text models using YouTube videos. It takes the audio of the video and the subtitles added by the user, then processes
the audio through the speech to text model to get transcriptions, and compares them with the subtitles added by the
user.

To use the speech to text testing framework, users will need to define normalizing, transcribing, and comparing
functions specific to their speech to text model and testing needs. These functions will be used by the framework to
process the audio and compare it to the user-provided subtitles. \
The framework includes basic normalizing and comparing
functions in the [lib folder](https://github.com/Kowalski1024/speech-to-text-tester/tree/master/lib). It also includes a
TestBase class that users can use to create new tests. The TestBase
class is designed to be flexible and customizable, allowing users to define specific steps when processing a video.

At the moment, the framework is designed for testing [Whisper](https://github.com/openai/whisper), an open source model
from OpenAI.

## Test plan generation

The framework uses test plans generated
by [generator](https://github.com/Kowalski1024/speech-to-text-tester/blob/master/testplan_generator/generator.py) that
allows users to
specify the number of videos in the test, video category, and other relevant parameters. The generator collects videos
from the YouTube Data API and their corresponding transcripts using the YouTubeTranscriptApi library.

New iterations of tests can be created using previous tests as each test has a token to the next page of results from
the YouTube Data API. This allows for easy scalability and repeatability of the testing process, as users can easily
generate new test plans using previously test plans.

## Tester output

Once the framework has been run using the generated test plan, the results will have exactly the same structure as the
input test plan. However, each video in the test plan will now have
feedback from the framework, including the minimum average word error rate (ma WER) and the differences between the
transcripts generated by the speech to text model and the user-provided subtitles. Results are also saved in SQLite for
faster analysis.

## Usage

### Docker

Build image

```shell
docker build -t model-tester .
```

Run container

```shell
docker run  -e GoogleAPI=<YOUR KEY> --gpus all -d --name whisper-tester -it model-tester
```

### Example

Testplan generation

```shell
python testplan_generator/testplan_generator.py 2 -o ./testplans -c 28 -l en
```

Run test

```shell
python tests/transcript_diff.py base "/app/testplans/<TESTFILE>" -it 2
```
