import React from "react";
import {CalculateMetadataFunction, Composition} from "remotion";
import {ShunriReel} from "./ShunriReel";
import type {ShunriReelProps} from "./types";

const defaultProps: ShunriReelProps = {
  durationSeconds: 3,
  fps: 30,
  accentHex: "#FF7A00",
  audioSrc: "input/narration.wav",
  scenes: [],
};

const calculateMetadata: CalculateMetadataFunction<ShunriReelProps> = ({props}) => {
  const fps = Number.isFinite(props.fps) && props.fps > 0 ? props.fps : 30;
  const seconds =
    Number.isFinite(props.durationSeconds) && props.durationSeconds > 0
      ? props.durationSeconds
      : 3;

  return {
    durationInFrames: Math.max(1, Math.ceil(seconds * fps)),
    fps,
    width: 1080,
    height: 1920,
    defaultCodec: "h264",
    defaultPixelFormat: "yuv420p",
    props: {...props, fps, durationSeconds: seconds},
  };
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="ShunriReel"
      component={ShunriReel}
      durationInFrames={90}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaultProps}
      calculateMetadata={calculateMetadata}
    />
  );
};
