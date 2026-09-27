import React from "react";
import {AbsoluteFill, interpolate, staticFile, useCurrentFrame, useVideoConfig} from "remotion";
import {Video} from "@remotion/media";
import type {Scene} from "../types";
import {OverlayCard} from "./OverlayCard";

const cameraTransform = (
  name: string | undefined,
  frame: number,
  durationInFrames: number,
): string => {
  const p = durationInFrames <= 1 ? 1 : frame / (durationInFrames - 1);
  if (name === "punch-in") {
    const scale = interpolate(p, [0, 0.18, 1], [1, 1.11, 1.12]);
    return `scale(${scale})`;
  }
  if (name === "drift-left") return `scale(1.06) translateX(${18 - p * 36}px)`;
  if (name === "drift-right") return `scale(1.06) translateX(${-18 + p * 36}px)`;
  if (name === "cta-push") return `scale(${1 + p * 0.07})`;
  if (name === "slow-push") return `scale(${1 + p * 0.05})`;
  return `scale(1.03) translateX(${Math.sin(p * Math.PI * 2) * 5}px)`;
};

export const PresenterScene: React.FC<{scene: Scene; durationInFrames: number}> = ({
  scene,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const fadeFrames = Math.max(4, Math.round(fps * 0.14));
  const fadeIn = interpolate(frame, [0, fadeFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [Math.max(0, durationInFrames - fadeFrames), durationInFrames],
    [1, 0],
    {extrapolateLeft: "clamp", extrapolateRight: "clamp"},
  );
  const opacity = Math.min(fadeIn, fadeOut);
  const layout = scene.layoutVariant ?? "center";
  const transform = cameraTransform(scene.cameraMotion, frame, durationInFrames);
  const src = staticFile(scene.presenterSrc);

  const Background = () => (
    <Video
      src={src}
      muted
      loop
      objectFit="cover"
      style={{
        position: "absolute",
        inset: -45,
        width: 1170,
        height: 2010,
        transform,
        filter:
          layout === "fullscreen-card"
            ? "blur(24px) brightness(.48) saturate(.78)"
            : layout === "center"
              ? "brightness(.86)"
              : "blur(22px) brightness(.55)",
      }}
    />
  );

  return (
    <AbsoluteFill style={{backgroundColor: "#101010", opacity, overflow: "hidden"}}>
      <Background />
      {layout !== "center" && layout !== "fullscreen-card" ? (
        <div
          style={{
            position: "absolute",
            top: 250,
            bottom: 250,
            width: 760,
            left: layout === "left-presenter" ? 40 : undefined,
            right: layout === "right-presenter" ? 40 : undefined,
            overflow: "hidden",
            borderRadius: 38,
            boxShadow: "0 30px 90px rgba(0,0,0,.28)",
          }}
        >
          <Video
            src={src}
            muted
            loop
            objectFit="cover"
            style={{width: "100%", height: "100%", transform}}
          />
        </div>
      ) : null}
      {layout === "fullscreen-card" ? (
        <div
          style={{
            position: "absolute",
            inset: "165px 55px 245px",
            borderRadius: 46,
            background: "rgba(0,0,0,.20)",
            border: "1px solid rgba(255,255,255,.12)",
          }}
        />
      ) : null}
      {scene.overlaySrc ? (
        <OverlayCard src={scene.overlaySrc} fullscreen={layout === "fullscreen-card"} />
      ) : null}
    </AbsoluteFill>
  );
};
