export type Scene = {
  id: string;
  type: string;
  caption: string;
  start: number;
  end: number;
  presenterVariant: string;
  presenterSrc: string;
  cameraMotion?: string;
  layoutVariant?: "center" | "left-presenter" | "right-presenter" | "fullscreen-card";
  overlaySrc?: string | null;
};

export type ShunriReelProps = {
  durationSeconds: number;
  fps: number;
  accentHex: string;
  audioSrc: string;
  scenes: Scene[];
};
