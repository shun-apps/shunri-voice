import React from "react";
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from "remotion";
import {Video} from "@remotion/media";
import type {Scene} from "../types";

const Media: React.FC<{scene: Scene}> = ({scene}) => {
  if (!scene.resolvedAssetSrc) return null;
  const src = staticFile(scene.resolvedAssetSrc);
  if (scene.assetResolution?.kind === "video") {
    return (
      <Video
        src={src}
        muted
        loop
        objectFit="cover"
        style={{width: "100%", height: "100%"}}
      />
    );
  }
  return (
    <Img
      src={src}
      style={{width: "100%", height: "100%", objectFit: "cover"}}
    />
  );
};

export const BrollVisual: React.FC<{
  scene: Scene;
  durationInFrames: number;
}> = ({scene, durationInFrames}) => {
  const frame = useCurrentFrame();
  const progress =
    durationInFrames <= 1 ? 1 : Math.min(1, frame / (durationInFrames - 1));
  const fadeFrames = Math.max(
    1,
    Math.min(6, Math.floor(Math.max(3, durationInFrames) / 3)),
  );
  const fadeIn =
    durationInFrames <= 2
      ? 1
      : interpolate(frame, [0, fadeFrames], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
  const fadeOut =
    durationInFrames <= 2
      ? 1
      : interpolate(
          frame,
          [Math.max(fadeFrames, durationInFrames - fadeFrames), durationInFrames],
          [1, 0],
          {extrapolateLeft: "clamp", extrapolateRight: "clamp"},
        );
  const opacity = Math.min(fadeIn, fadeOut);

  return (
    <AbsoluteFill
      style={{
        opacity,
        overflow: "hidden",
        backgroundColor: "#080808",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: -30,
          transform: `scale(${1.05 + progress * 0.055}) translateX(${-14 + progress * 28}px)`,
        }}
      >
        <Media scene={scene} />
      </div>
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,.20), rgba(0,0,0,.02) 42%, rgba(0,0,0,.60) 82%, rgba(0,0,0,.78))",
        }}
      />
    </AbsoluteFill>
  );
};
