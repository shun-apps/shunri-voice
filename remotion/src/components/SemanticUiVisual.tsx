import React from "react";
import {interpolate, spring, useCurrentFrame, useVideoConfig} from "remotion";
import type {Scene} from "../types";

const inferLabel = (caption: string): string => {
  const text = caption.toLowerCase();
  if (text.includes("canva")) return "CANVA";
  if (text.includes("chatgpt")) return "CHATGPT";
  if (text.includes("figma")) return "FIGMA";
  if (text.includes("notion")) return "NOTION";
  if (text.includes("ブラウザ") || text.includes("サイト")) return "WEB";
  if (text.includes("設定")) return "SETTINGS";
  return "APP / UI";
};

export const SemanticUiVisual: React.FC<{
  scene: Scene;
  durationInFrames: number;
}> = ({scene, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({
    frame,
    fps,
    durationInFrames: Math.max(10, Math.round(fps * 0.34)),
    config: {damping: 19, stiffness: 150, mass: 0.82},
  });
  const progress =
    durationInFrames <= 1 ? 1 : Math.min(1, frame / (durationInFrames - 1));
  const exit = interpolate(
    frame,
    [Math.max(0, durationInFrames - Math.round(fps * 0.16)), durationInFrames],
    [1, 0],
    {extrapolateLeft: "clamp", extrapolateRight: "clamp"},
  );
  const label = inferLabel(scene.caption);

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        background:
          "linear-gradient(180deg, rgba(8,8,8,.56), rgba(8,8,8,.16) 45%, rgba(8,8,8,.70))",
        opacity: exit,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 205,
          left: 72,
          right: 72,
          bottom: 360,
          borderRadius: 42,
          overflow: "hidden",
          background: "rgba(247,247,247,.98)",
          border: "1px solid rgba(255,255,255,.72)",
          boxShadow: "0 34px 120px rgba(0,0,0,.52)",
          transform: `translateY(${(1 - enter) * -86}px) scale(${0.93 + enter * 0.07})`,
          opacity: enter * exit,
        }}
      >
        <div
          style={{
            height: 82,
            display: "flex",
            alignItems: "center",
            padding: "0 28px",
            gap: 14,
            background: "#ececec",
            borderBottom: "1px solid rgba(0,0,0,.08)",
          }}
        >
          {["#ff5f57", "#febc2e", "#28c840"].map((color) => (
            <span
              key={color}
              style={{width: 19, height: 19, borderRadius: 999, background: color}}
            />
          ))}
          <div
            style={{
              marginLeft: 8,
              height: 34,
              flex: 1,
              borderRadius: 999,
              background: "white",
              boxShadow: "inset 0 0 0 1px rgba(0,0,0,.06)",
            }}
          />
        </div>

        <div style={{display: "flex", height: "calc(100% - 82px)"}}>
          <div
            style={{
              width: 190,
              padding: "30px 22px",
              background: "#f3f3f3",
              borderRight: "1px solid rgba(0,0,0,.07)",
            }}
          >
            <div
              style={{
                fontFamily: '"Noto Sans CJK JP", sans-serif',
                fontWeight: 900,
                fontSize: 24,
                letterSpacing: "0.06em",
                color: "#171717",
                marginBottom: 30,
              }}
            >
              {label}
            </div>
            {[0, 1, 2, 3, 4].map((n) => (
              <div
                key={n}
                style={{
                  height: 18,
                  borderRadius: 999,
                  marginBottom: 24,
                  width: n % 2 ? "70%" : "88%",
                  background: n === 0 ? "#111" : "#d9d9d9",
                  opacity: n === 0 ? 0.9 : 1,
                }}
              />
            ))}
          </div>

          <div style={{flex: 1, padding: "34px 34px 40px", overflow: "hidden"}}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 28,
              }}
            >
              <div
                style={{
                  width: 300,
                  height: 32,
                  borderRadius: 999,
                  background: "#181818",
                }}
              />
              <div
                style={{
                  width: 120,
                  height: 42,
                  borderRadius: 14,
                  background: "#ff6a00",
                }}
              />
            </div>

            <div
              style={{
                height: 330,
                borderRadius: 28,
                background:
                  "linear-gradient(135deg, #242424 0%, #424242 48%, #ff6a00 140%)",
                marginBottom: 30,
                padding: 34,
                transform: `translateX(${progress * -8}px)`,
              }}
            >
              <div
                style={{
                  fontFamily: '"Noto Sans CJK JP", sans-serif',
                  color: "white",
                  fontWeight: 900,
                  fontSize: 52,
                  lineHeight: 1.08,
                  maxWidth: 520,
                }}
              >
                {label}
              </div>
              <div
                style={{
                  marginTop: 24,
                  width: "72%",
                  height: 22,
                  borderRadius: 999,
                  background: "rgba(255,255,255,.70)",
                }}
              />
              <div
                style={{
                  marginTop: 14,
                  width: "50%",
                  height: 22,
                  borderRadius: 999,
                  background: "rgba(255,255,255,.34)",
                }}
              />
            </div>

            <div style={{display: "flex", gap: 22}}>
              {[0, 1, 2].map((n) => (
                <div
                  key={n}
                  style={{
                    flex: 1,
                    height: 235,
                    borderRadius: 24,
                    background: n === 1 ? "#eee5de" : "#e9e9e9",
                    border: "1px solid rgba(0,0,0,.06)",
                    transform: `translateY(${(n - 1) * progress * 5}px)`,
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
