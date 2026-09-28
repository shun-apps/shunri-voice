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
  visualDirection?: {visualType: string; reason?: string; confidence?: number; symbol?: string; assetQuery?: string};
  assetResolution?: {
    status: "resolved" | "missing" | "not-required";
    kind?: "image" | "video";
    relativePath?: string;
    source?: string;
    reason?: string;
    query?: string;
    requiredKinds?: string[];
  };
  resolvedAssetSrc?: string | null;
};

export type ShunriReelProps = {
  durationSeconds: number;
  fps: number;
  accentHex: string;
  audioSrc: string;
  scenes: Scene[];
};
