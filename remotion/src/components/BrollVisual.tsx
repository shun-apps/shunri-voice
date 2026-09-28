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
  const opacity = interpolate(
    frame,
    [0, Math.min(6, Math.max(1, durationInFrames - 1)), Math.max(0, durationInFrames - 6), durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: "clamp", extrapolateRight: "clamp"},
  );

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
