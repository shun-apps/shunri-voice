import React from "react";
import {Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from "remotion";
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
        objectFit="contain"
        style={{width: "100%", height: "100%"}}
      />
    );
  }
  return (
    <Img
      src={src}
      style={{width: "100%", height: "100%", objectFit: "contain"}}
    />
  );
};

export const ScreenshotVisual: React.FC<{
  scene: Scene;
  durationInFrames: number;
}> = ({scene, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({
    frame,
    fps,
    durationInFrames: Math.max(10, Math.round(fps * 0.34)),
    config: {damping: 18, stiffness: 145, mass: 0.82},
  });
  const exit = interpolate(
    frame,
    [Math.max(0, durationInFrames - Math.round(fps * 0.18)), durationInFrames],
    [1, 0],
    {extrapolateLeft: "clamp", extrapolateRight: "clamp"},
  );
  const progress =
    durationInFrames <= 1 ? 1 : Math.min(1, frame / (durationInFrames - 1));

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        background:
          "linear-gradient(180deg, rgba(5,5,5,.58), rgba(5,5,5,.22) 44%, rgba(5,5,5,.72))",
        opacity: exit,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 185,
          left: 70,
          right: 70,
          bottom: 330,
          borderRadius: 42,
          overflow: "hidden",
          background: "#f6f6f6",
          border: "1px solid rgba(255,255,255,.7)",
          boxShadow: "0 36px 110px rgba(0,0,0,.54)",
          transform: `translateY(${(1 - enter) * -110}px) scale(${0.91 + enter * 0.09}) rotate(${(1 - enter) * -1.4}deg)`,
          transformOrigin: "50% 45%",
          opacity: enter * exit,
        }}
      >
        <div
          style={{
            height: 76,
            display: "flex",
            alignItems: "center",
            gap: 14,
            padding: "0 24px",
            background: "rgba(235,235,235,.98)",
            borderBottom: "1px solid rgba(0,0,0,.08)",
          }}
        >
          {["#ff5f57", "#febc2e", "#28c840"].map((color) => (
            <span
              key={color}
              style={{
                width: 19,
                height: 19,
                borderRadius: 999,
                background: color,
                boxShadow: "inset 0 0 0 1px rgba(0,0,0,.08)",
              }}
            />
          ))}
          <div
            style={{
              marginLeft: 10,
              height: 34,
              flex: 1,
              borderRadius: 999,
              background: "rgba(255,255,255,.92)",
              boxShadow: "inset 0 0 0 1px rgba(0,0,0,.06)",
            }}
          />
        </div>
        <div
          style={{
            position: "absolute",
            top: 76,
            left: 0,
            right: 0,
            bottom: 0,
            overflow: "hidden",
            background: "white",
          }}
        >
          <div
            style={{
              width: "100%",
              height: "100%",
              transform: `scale(${1 + progress * 0.025}) translateY(${-8 * progress}px)`,
            }}
          >
            <Media scene={scene} />
          </div>
        </div>
      </div>
    </div>
  );
};
