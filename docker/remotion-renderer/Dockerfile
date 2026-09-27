FROM node:22-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
  libnss3 \
  libdbus-1-3 \
  libatk1.0-0 \
  libgbm-dev \
  libasound2 \
  libxrandr2 \
  libxkbcommon-dev \
  libxfixes3 \
  libxcomposite1 \
  libxdamage1 \
  libatk-bridge2.0-0 \
  libpango-1.0-0 \
  libcairo2 \
  libcups2 \
  fonts-noto-cjk \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY remotion/package.json ./package.json
COPY remotion/tsconfig.json ./tsconfig.json
RUN npm install --no-audit --no-fund

COPY remotion/src ./src
RUN npm run typecheck
RUN npx remotion browser ensure

RUN mkdir -p /app/public /output

CMD ["npx", "remotion", "render", "src/index.ts", "ShunriReel", "/output/shunri-reel-remotion.mp4", "--props=/app/public/input/remotion-props.json", "--codec=h264", "--pixel-format=yuv420p", "--crf=20", "--concurrency=1", "--log=info"]
