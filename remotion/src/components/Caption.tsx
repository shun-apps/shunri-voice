import React from "react";
import {interpolate, spring, useCurrentFrame, useVideoConfig} from "remotion";

const HERO_PATTERN = /(ファーストビュー|仕事が減らない|仕事の流れ|\d+(?:\.\d+)?(?:時間|分|秒|倍|%|％))/;

export const isHeroBeat = (text: string): boolean => HERO_PATTERN.test(text);

const chunkText = (text: string, max = 18): string[] => {
  const clean = text.trim();
  if (!clean) return [];
  if (clean.length <= max) return [clean];

  const chunks: string[] = [];
  const punctuation = clean.split(/(?<=[。、！？!?])/u).filter(Boolean);
  for (const part of punctuation) {
    let rest = part.trim();
    while (rest.length > max) {
      chunks.push(Array.from(rest).slice(0, max).join(""));
      rest = Array.from(rest).slice(max).join("");
    }
    if (rest) chunks.push(rest);
  }
  return chunks;
};

export const buildCaptionBeats = (caption: string): string[] => {
  const parts = caption
    .split(/(ファーストビュー|仕事が減らない|仕事の流れ|\d+(?:\.\d+)?(?:時間|分|秒|倍|%|％))/u)
    .map((part) => part.trim())
    .filter(Boolean);

  const beats: string[] = [];
  for (const part of parts) {
    if (isHeroBeat(part)) beats.push(part);
    else beats.push(...chunkText(part));
  }
  return beats.length ? beats : [caption];
};

type CaptionBeatProps = {
  text: string;
  accentHex: string;
  hero: boolean;
  durationInFrames: number;
};

export const CaptionBeat: React.FC<CaptionBeatProps> = ({
  text,
  accentHex,
  hero,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({
    fps,
    frame,
    config: {damping: 17, stiffness: hero ? 180 : 150, mass: 0.72},
    durationInFrames: Math.max(8, Math.round(fps * 0.28)),
  });
  const fadeOut = interpolate(
    frame,
    [Math.max(0, durationInFrames - Math.round(fps * 0.18)), durationInFrames],
    [1, 0],
    {extrapolateLeft: "clamp", extrapolateRight: "clamp"},
  );

  if (hero) {
    return (
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "0 70px",
          pointerEvents: "none",
          opacity: fadeOut,
        }}
      >
        <div
          style={{
            transform: `scale(${0.82 + enter * 0.18}) translateY(${(1 - enter) * 20}px)`,
            fontFamily: '"Noto Sans CJK JP", sans-serif',
            fontSize: 122,
            fontWeight: 900,
            lineHeight: 1.08,
            letterSpacing: "-0.04em",
            textAlign: "center",
            color: accentHex,
            textShadow: "0 5px 0 rgba(0,0,0,.42), 0 12px 34px rgba(0,0,0,.6)",
            WebkitTextStroke: "2px rgba(20,20,20,.72)",
          }}
        >
          {text}
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        position: "absolute",
        left: 70,
        right: 70,
        bottom: 235,
        display: "flex",
        justifyContent: "center",
        pointerEvents: "none",
        opacity: enter * fadeOut,
        transform: `translateY(${(1 - enter) * 22}px)`,
      }}
    >
      <div
        style={{
          maxWidth: 920,
          padding: "18px 28px 20px",
          borderRadius: 22,
          background: "rgba(0,0,0,.36)",
          backdropFilter: "blur(6px)",
          fontFamily: '"Noto Sans CJK JP", sans-serif',
          fontSize: 66,
          fontWeight: 850,
          lineHeight: 1.22,
          letterSpacing: "-0.03em",
          textAlign: "center",
          color: "white",
          textShadow: "0 4px 12px rgba(0,0,0,.85)",
        }}
      >
        {text}
      </div>
    </div>
  );
};
