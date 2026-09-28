import React from "react";
import {interpolate, spring, useCurrentFrame, useVideoConfig} from "remotion";
import type {Scene} from "../types";
import {BrollVisual} from "./BrollVisual";
import {ScreenshotVisual} from "./ScreenshotVisual";

const GraphicVisual: React.FC<{
  scene: Scene;
  accentHex: string;
}> = ({scene, accentHex}) => {
  const direction = scene.visualDirection;
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({
    frame,
    fps,
    config: {damping: 15, stiffness: 190, mass: 0.7},
  });
  const opacity = interpolate(
    frame,
    [0, Math.max(4, Math.round(fps * 0.12))],
    [0, 1],
    {extrapolateRight: "clamp"},
  );
  const base: React.CSSProperties = {
    position: "absolute",
    inset: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    pointerEvents: "none",
    opacity,
    transform: `scale(${0.78 + 0.22 * pop})`,
    fontFamily: '"Noto Sans CJK JP", sans-serif',
  };

  if (!direction) return null;

  if (direction.visualType === "symbol") {
    return (
      <div
        style={{
          ...base,
          fontSize: 520,
          fontWeight: 900,
          color: direction.symbol === "×" ? "#ff453a" : "#34c759",
          textShadow: "0 20px 70px rgba(0,0,0,.65)",
        }}
      >
        {direction.symbol ?? "○"}
      </div>
    );
  }

  if (direction.visualType === "hero") {
    return (
      <div
        style={{
          ...base,
          padding: "0 80px",
          fontSize: 112,
          fontWeight: 950,
          lineHeight: 1.05,
          textAlign: "center",
          color: accentHex,
          textShadow: "0 8px 35px rgba(0,0,0,.8)",
        }}
      >
        {scene.caption}
      </div>
    );
  }

  if (direction.visualType === "comparison") {
    return (
      <div style={{...base, gap: 26, padding: 70}}>
        <div
          style={{
            flex: 1,
            padding: 42,
            borderRadius: 36,
            background: "rgba(255,69,58,.9)",
            fontSize: 62,
            fontWeight: 900,
          }}
        >
          BEFORE
        </div>
        <div style={{fontSize: 86, fontWeight: 900}}>→</div>
        <div
          style={{
            flex: 1,
            padding: 42,
            borderRadius: 36,
            background: "rgba(52,199,89,.9)",
            fontSize: 62,
            fontWeight: 900,
          }}
        >
          AFTER
        </div>
      </div>
    );
  }

  if (direction.visualType === "card") {
    return (
      <div style={{...base, padding: 70}}>
        <div
          style={{
            padding: "48px 52px",
            borderRadius: 38,
            background: "rgba(255,255,255,.94)",
            color: "#111",
            fontSize: 68,
            fontWeight: 900,
            lineHeight: 1.18,
            textAlign: "center",
            boxShadow: "0 24px 80px rgba(0,0,0,.45)",
          }}
        >
          {scene.caption}
        </div>
      </div>
    );
  }

  return null;
};

export const DirectedVisual: React.FC<{
  scene: Scene;
  accentHex: string;
  durationInFrames: number;
}> = ({scene, accentHex, durationInFrames}) => {
  const direction = scene.visualDirection;
  if (!direction || direction.visualType === "presenter" || direction.visualType === "cta") {
    return null;
  }

  if (direction.visualType === "screenshot") {
    return scene.resolvedAssetSrc ? (
      <ScreenshotVisual scene={scene} durationInFrames={durationInFrames} />
    ) : null;
  }

  if (direction.visualType === "b-roll") {
    return scene.resolvedAssetSrc ? (
      <BrollVisual scene={scene} durationInFrames={durationInFrames} />
    ) : null;
  }

  return <GraphicVisual scene={scene} accentHex={accentHex} />;
};
