from typing import Iterable
import argparse
from pathlib import Path
from os import PathLike
import pprint
import json
import os
import time

from loguru import logger

from libs.youtube_video import YouTubeVideo
from testrunners import TestRunner, TestRegistry
from testrunners.tests.tests import TranscriptDifference
from generators.youtube_generator import generate


@TestRegistry.register(TranscriptDifference)
class YouTubeTestRunner(TestRunner):
    """
    Test runner for youtube videos, uses a testplan generated by youtube_generator
    """

    def __init__(
        self,
        testplan_path: PathLike,
        audio_dir: PathLike,
        iterations: int = 1,
        save_transcripts: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self._audio_dir = Path(audio_dir)
        self._testplan_path = Path(testplan_path)
        self._iterations = iterations
        self._save_transcripts = save_transcripts

    def run(self) -> None:
        if self.tester.transcriber is None:
            raise ValueError("Transcriber is None")

        if self.tester.normalizer is None:
            logger.warning("Normalizer is None, running without normalizer")

        # check if we can generate more testplans if we need to
        if self._iterations > 1 and "GoogleAPI" not in os.environ:
            raise ValueError(
                "GoogleAPI not in the environment, can not generate more test plans. "
                "Add GoogleAPI or set iterations to 1."
            )

        with open(self._testplan_path) as f:
            testplan = json.load(f)

        # run the testplan
        for i in range(self._iterations):
            logger.info(f"Starting {i + 1}/{self._iterations} testplan")
            logger.info(f"Testplan args:\n{pprint.pformat(testplan['args'])}")

            # iterate over the videos in the testplan
            for idx, video_details in enumerate(self.video_details(testplan)):
                logger.info(
                    f"Testplan status: {idx + 1}/{len(testplan['items'])} video, {i + 1}/{self._iterations} testplan"
                )

                # download the audio
                video = YouTubeVideo.from_dict(video_details)
                try:
                    audio = video.download_mp3(self._audio_dir)
                except ValueError as e:
                    logger.warning(
                        f"Skipping the video {video.videoId}, ValueError (download): {e}"
                    )
                    video_details["error"] = f"ValueError (download): {e}"
                    continue

                # transcribe the audio
                try:
                    model_transcript = self.tester.transcribe(audio)
                except TimeoutError as e:
                    logger.warning(
                        f"Skipping the video {video.videoId}, TimeoutError (model transcript): {e}"
                    )
                    video_details["error"] = f"TimeoutError (model transcript): {e}"
                    continue

                # download the target transcript
                try:
                    target_transcript = video.youtube_transcript(self.tester.language)
                except ValueError as e:
                    logger.warning(
                        f"Skipping the video {video.videoId}, ValueError (youtube transcript): {e}"
                    )
                    video_details["error"] = f"ValueError (youtube transcript): {e}"
                    continue

                # compare the transcripts
                results = self.tester.compare(model_transcript, target_transcript)
                video_details["results"] = results

                # add the transcripts to the video details if we want to save them
                if self._save_transcripts:
                    video_details["modelTranscript"] = model_transcript
                    video_details["targetTranscript"] = target_transcript

            self.tester.testplan_postprocess(testplan)
            self.save_results(testplan)

            # generate a new testplan if we need to
            if i + 1 < self._iterations:
                args = testplan["args"]
                args["pageToken"] = testplan["nextPageToken"]
                testplan = generate(args)

    @staticmethod
    def video_details(testplan: dict) -> Iterable[dict]:
        """
        Args:
            testplan: testplan generated by youtube_generator

        Returns:
            Generator of video details
        """

        videos = testplan["items"]

        for video_details in videos:
            yield video_details

    @classmethod
    def save_results(cls, results) -> None:
        """
        Save the results to a json file

        Args:
            results: results to save
        """

        time_str = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{cls.__name__}_{time_str}.json"

        path = Path(__file__).parent.joinpath("output", filename)
        path.parent.mkdir(exist_ok=True)

        logger.info(f"Saving results - {path}")

        with open(path, "x", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

    @staticmethod
    def runner_args(parser: argparse.ArgumentParser) -> None:
        """
        Add runner specific arguments to the parser

        Args:
            parser: parser to add arguments to
        """

        parser.add_argument(type=str, dest="testplan_path", help="Testplan path")

        parser.add_argument(
            "-st",
            "--save-transcript",
            required=False,
            action="store_true",
            dest="save_transcripts",
            default=False,
        )

        parser.add_argument(
            "-ap",
            "--audio-path",
            required=False,
            type=str,
            default="./cache/audio",
            dest="audio_dir",
        )

        parser.add_argument("-it", "--iterations", required=False, type=int, default=1)


if __name__ == "__main__":
    YouTubeTestRunner.from_command_line().run()
