import React from "react";
import {Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from "remotion";

type Props = {
  src: string;
  fullscreen: boolean;
};

export const OverlayCard: React.FC<Props> = ({src, fullscreen}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const enter = spring({
    fps,
    frame,
    durationInFrames: Math.max(10, Math.round(fps * 0.34)),
    config: {damping: 18, stiffness: 150, mass: 0.8},
  });
  const exit = interpolate(
    frame,
    [Math.max(0, durationInFrames - Math.round(fps * 0.22)), durationInFrames],
    [1, 0],
    {extrapolateLeft: "clamp", extrapolateRight: "clamp"},
  );

  return (
    <div
      style={{
        position: "absolute",
        top: fullscreen ? 250 : 120,
        left: fullscreen ? 76 : 120,
        right: fullscreen ? 76 : 120,
        height: fullscreen ? 1330 : 610,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity: enter * exit,
        transform: `translateY(${(1 - enter) * -90}px) scale(${0.94 + enter * 0.06})`,
        borderRadius: 36,
        overflow: "hidden",
        background: "rgba(255,255,255,.96)",
        boxShadow: "0 24px 80px rgba(0,0,0,.36)",
        border: "2px solid rgba(255,255,255,.68)",
      }}
    >
      <Img
        src={staticFile(src)}
        style={{width: "100%", height: "100%", objectFit: "contain"}}
      />
    </div>
  );
};
