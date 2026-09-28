import React from "react";
import {AbsoluteFill, Sequence, staticFile, useVideoConfig} from "remotion";
import {Audio} from "@remotion/media";
import type {ShunriReelProps} from "./types";
import {PresenterScene} from "./components/PresenterScene";
import {buildCaptionBeats, CaptionBeat, isHeroBeat} from "./components/Caption";
import {DirectedVisual} from "./components/DirectedVisual";

const SceneCaptions: React.FC<{
  caption: string;
  accentHex: string;
  durationInFrames: number;
}> = ({caption, accentHex, durationInFrames}) => {
  const beats = buildCaptionBeats(caption);
  const weights = beats.map((beat) => Math.max(2, Array.from(beat).length));
  const totalWeight = weights.reduce((sum, value) => sum + value, 0);
  let cursor = 0;

  return (
    <>
      {beats.map((beat, index) => {
        const remaining = durationInFrames - cursor;
        const raw =
          index === beats.length - 1
            ? remaining
            : Math.max(
                6,
                Math.round((durationInFrames * weights[index]) / totalWeight),
              );
        const beatDuration = Math.max(1, Math.min(remaining, raw));
        const from = cursor;
        cursor += beatDuration;
        return (
          <Sequence key={`${beat}-${index}`} from={from} durationInFrames={beatDuration}>
            <CaptionBeat
              text={beat}
              accentHex={accentHex}
              hero={isHeroBeat(beat)}
              durationInFrames={beatDuration}
            />
          </Sequence>
        );
      })}
    </>
  );
};

export const ShunriReel: React.FC<ShunriReelProps> = ({
  audioSrc,
  scenes,
  accentHex,
}) => {
  const {fps} = useVideoConfig();

  return (
    <AbsoluteFill style={{backgroundColor: "#0b0b0b"}}>
      <Audio src={staticFile(audioSrc)} />
      {scenes.map((scene, index) => {
        const from = Math.max(0, Math.round(scene.start * fps));
        const durationInFrames = Math.max(
          1,
          Math.round((scene.end - scene.start) * fps),
        );
        const visualType = scene.visualDirection?.visualType;
        const hideDefaultCaptions =
          visualType === "hero" || visualType === "card" || visualType === "cta";
        return (
          <Sequence
            key={scene.id}
            name={scene.id}
            from={from}
            durationInFrames={durationInFrames}
          >
            <PresenterScene
              scene={scene}
              durationInFrames={durationInFrames}
              isFirstScene={index === 0}
            />
            <DirectedVisual
              scene={scene}
              accentHex={accentHex}
              durationInFrames={durationInFrames}
            />
            {!hideDefaultCaptions ? (
              <SceneCaptions
                caption={scene.caption}
                accentHex={accentHex}
                durationInFrames={durationInFrames}
              />
            ) : null}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
