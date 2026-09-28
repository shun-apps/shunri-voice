import React from "react";
import {interpolate, spring, useCurrentFrame, useVideoConfig} from "remotion";
import type {Scene} from "../types";
import {BrollVisual} from "./BrollVisual";
import {ScreenshotVisual} from "./ScreenshotVisual";
import {SemanticUiVisual} from "./SemanticUiVisual";

const GraphicVisual: React.FC<{scene: Scene; accentHex: string}> = ({scene, accentHex}) => {
  const direction = scene.visualDirection;
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({
    frame,
    fps,
    config: {damping: 17, stiffness: 170, mass: 0.74},
  });
  const opacity = interpolate(
    frame,
    [0, Math.max(4, Math.round(fps * 0.12))],
    [0, 1],
    {extrapolateRight: "clamp"},
  );

  if (!direction) return null;

  if (direction.visualType === "symbol") {
    const negative = direction.symbol === "×";
    const tone = negative ? "#ff453a" : "#34c759";
    return (
      <div
        style={{
          position: "absolute",
          top: 300,
          right: 76,
          width: 260,
          height: 260,
          borderRadius: 48,
          background: "rgba(12,12,12,.64)",
          border: `3px solid ${tone}`,
          boxShadow: "0 28px 90px rgba(0,0,0,.44)",
          backdropFilter: "blur(10px)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          opacity,
          transform: `translateY(${(1 - enter) * -28}px) scale(${0.9 + enter * 0.1})`,
          pointerEvents: "none",
          fontFamily: '"Noto Sans CJK JP", sans-serif',
        }}
      >
        <div style={{fontSize: 32, fontWeight: 900, letterSpacing: "0.08em", color: tone}}>
          {negative ? "NG" : "OK"}
        </div>
        <div style={{fontSize: 160, lineHeight: 0.95, fontWeight: 950, color: tone}}>
          {direction.symbol ?? "○"}
        </div>
      </div>
    );
  }

  if (direction.visualType === "hero") {
    return (
      <div
        style={{
          position: "absolute",
          left: 72,
          right: 72,
          bottom: 285,
          padding: "30px 34px 34px",
          borderRadius: 34,
          background: "rgba(12,12,12,.72)",
          border: "1px solid rgba(255,255,255,.16)",
          boxShadow: "0 26px 90px rgba(0,0,0,.42)",
          backdropFilter: "blur(10px)",
          opacity,
          transform: `translateY(${(1 - enter) * 26}px)`,
          pointerEvents: "none",
          fontFamily: '"Noto Sans CJK JP", sans-serif',
        }}
      >
        <div
          style={{
            fontSize: 24,
            fontWeight: 900,
            letterSpacing: "0.12em",
            color: accentHex,
            marginBottom: 14,
          }}
        >
          KEY POINT
        </div>
        <div
          style={{
            fontSize: 74,
            fontWeight: 950,
            lineHeight: 1.1,
            color: "white",
            letterSpacing: "-0.035em",
          }}
        >
          {scene.caption}
        </div>
      </div>
    );
  }

  if (direction.visualType === "comparison") {
    return (
      <div
        style={{
          position: "absolute",
          inset: "250px 65px 330px",
          display: "flex",
          gap: 24,
          alignItems: "center",
          opacity,
          transform: `scale(${0.94 + enter * 0.06})`,
          pointerEvents: "none",
          fontFamily: '"Noto Sans CJK JP", sans-serif',
        }}
      >
        <div style={{flex: 1, padding: 34, borderRadius: 32, background: "rgba(255,69,58,.92)", fontSize: 56, fontWeight: 900}}>
          BEFORE
        </div>
        <div style={{fontSize: 72, fontWeight: 900, color: "white"}}>→</div>
        <div style={{flex: 1, padding: 34, borderRadius: 32, background: "rgba(52,199,89,.92)", fontSize: 56, fontWeight: 900}}>
          AFTER
        </div>
      </div>
    );
  }

  if (direction.visualType === "card") {
    return (
      <div
        style={{
          position: "absolute",
          left: 68,
          right: 68,
          top: 420,
          padding: "34px 38px 40px",
          borderRadius: 36,
          background: "rgba(255,255,255,.95)",
          boxShadow: "0 28px 95px rgba(0,0,0,.40)",
          opacity,
          transform: `translateY(${(1 - enter) * 34}px) scale(${0.96 + enter * 0.04})`,
          pointerEvents: "none",
          fontFamily: '"Noto Sans CJK JP", sans-serif',
        }}
      >
        <div style={{fontSize: 22, fontWeight: 900, letterSpacing: "0.12em", color: "#ff6a00", marginBottom: 12}}>
          POINT
        </div>
        <div style={{fontSize: 62, fontWeight: 900, lineHeight: 1.18, color: "#111", letterSpacing: "-0.03em"}}>
          {scene.caption}
        </div>
      </div>
    );
  }

  if (direction.visualType === "cta") {
    return (
      <div
        style={{
          position: "absolute",
          left: 64,
          right: 64,
          bottom: 230,
          padding: "34px 38px 38px",
          borderRadius: 36,
          background: "rgba(16,16,16,.88)",
          border: `2px solid ${accentHex}`,
          boxShadow: "0 30px 100px rgba(0,0,0,.48)",
          opacity,
          transform: `translateY(${(1 - enter) * 28}px)`,
          pointerEvents: "none",
          fontFamily: '"Noto Sans CJK JP", sans-serif',
        }}
      >
        <div style={{fontSize: 24, fontWeight: 900, letterSpacing: "0.12em", color: accentHex, marginBottom: 12}}>
          NEXT ACTION
        </div>
        <div style={{fontSize: 66, fontWeight: 950, lineHeight: 1.12, color: "white"}}>
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
  if (!direction || direction.visualType === "presenter") return null;

  if (direction.visualType === "screenshot") {
    return scene.resolvedAssetSrc ? (
      <ScreenshotVisual scene={scene} durationInFrames={durationInFrames} />
    ) : (
      <SemanticUiVisual scene={scene} durationInFrames={durationInFrames} />
    );
  }

  if (direction.visualType === "b-roll") {
    return scene.resolvedAssetSrc ? (
      <BrollVisual scene={scene} durationInFrames={durationInFrames} />
    ) : null;
  }

  return <GraphicVisual scene={scene} accentHex={accentHex} />;
};
