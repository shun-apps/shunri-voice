# shunri-voice

瞬LP AI広報「瞬理（しゅり）」の固定ナレーション音声を作るための Irodori-TTS 検証リポジトリです。

## 目的

最初から1つの声に固定せず、同じReel台本を5種類の声で生成して比較します。採用した声は、そのWAVを参照音声として以後の生成に使い、瞬理の声を固定していきます。

## 対応環境

- Apple Silicon Mac: Irodori-TTS をローカル実行（MPS / CPU）
- Intel Mac: 公式 Irodori-TTS-Server を Docker CPU で実行

Intel Mac では PyTorch 2.10 の macOS x86_64 wheel がないため、Mac本体には入れず Linux Docker 内で実行します。

## 1. セットアップ

    cd ~/shunri-voice
    git pull origin main
    make setup

### Apple Silicon Mac

uv がない場合:

    brew install uv
    make setup

### Intel Mac

Docker が必要です。

macOS 13以降なら Homebrew で導入できます。

    brew install --cask docker

macOS 12 Monterey では Homebrew の最新 Docker Desktop は入らないため、Docker公式リリースノートから **Docker Desktop 4.41.2 / Mac with Intel chip** を手動インストールしてください。

https://desktop.docker.com/mac/main/amd64/191736/Docker.dmg

Docker Desktop を起動してから:

    make setup

セットアップはCPU用 Docker イメージを構築し、Irodori-TTS API を localhost:8088 で起動します。Intel MacではCPU負荷を抑えるため、4ステップの MeanFlow 版 `Irodori-TTS-v4.1-Small-MF` を使用します。

## 2. 5種類の瞬理候補を一括生成

    make voices

生成先:

    outputs/voice-a.wav
    outputs/voice-b.wav
    outputs/voice-c.wav
    outputs/voice-d.wav
    outputs/voice-e.wav

初回生成時は Irodori-TTS モデルをダウンロードします。

台本は samples/reel_script.txt を編集すれば差し替えられます。

## 3. 採用した声を固定する

例: voice-b を採用した場合

    mkdir -p references
    cp outputs/voice-b.wav references/shunri.wav
    python3 scripts/generate.py --text-file samples/reel_script.txt --preset default --reference references/shunri.wav

参照音声を使うことで、話者IDを保ちながら台本ごとに話し方を調整できます。

Intel Mac では参照音声を Docker 側の voices/ に自動コピーして使用します。

## 4. Apple Silicon の MPS / CPU

通常は自動判定します。

    python3 scripts/generate.py --preset all --device mps

MPSで失敗した場合:

    python3 scripts/generate.py --preset all --device cpu

Intel Mac では --device 指定に関係なく Docker CPU API を利用します。

## 声候補

- A: 知的・落ち着き
- B: 軽いウィスパー
- C: 明るく親しみやすい
- D: クールなAI広報
- E: 自然なSNSクリエイター

## ライセンス / 注意

Irodori-TTS のコード・モデルの利用条件と Ethical Restrictions に従ってください。実在人物・声優・著名人などの声を本人の明示的同意なくクローンしないでください。本リポジトリはオリジナルAIキャラクター「瞬理」用の新規音声設計を前提にしています。

生成時の SilentCipher 電子透かしは Irodori-TTS 側の標準挙動をそのまま利用します。

## 構成

- config/voices.json: 声候補と固定後のデフォルト設定
- samples/reel_script.txt: 比較用Reel台本
- scripts/bootstrap.sh: 環境判定とセットアップ
- scripts/generate.py: 一括 / 単体音声生成
- outputs/: 生成音声（Git管理外）
- references/: 採用した参照音声（Git管理外）
- .vendor/Irodori-TTS/: Apple Silicon用本体（Git管理外）
- .vendor/Irodori-TTS-Server/: Intel Mac用公式APIサーバー（Git管理外）


## MP4 / MP3 から瞬理の固定声を登録

気に入っている声サンプルがある場合は、Voice Design でゼロから声を作るより、参照音声として登録する方が有効です。

MP4 / MP3 / WAV などをそのまま指定できます。

    make reference FILE="/path/to/voice-sample.mp4"

内部で音声だけを抽出し、Irodori-TTS向けの 48kHz / mono / PCM WAV に変換して、

    references/shunri.wav

へ保存します。

その後、固定声でテスト生成します。

    make shunri

生成先:

    outputs/clone.wav

Intel Mac では、ホストに ffmpeg がなくてもセットアップ済みの Docker イメージ内の ffmpeg を使って変換します。

参照音声はGit管理外なので、公開GitHubへアップロードされません。


## いつでも使える `shunri` コマンド

一度だけインストールします。

    cd ~/shunri-voice
    git pull origin main
    make install-cli
    source ~/.zshrc

以後は、どのフォルダにいても瞬理の固定声を呼び出せます。

文章を直接指定:

    shunri "こんにちは。瞬理です。今日はLPについて話します。"

生成後そのまま再生:

    shunri --play "こんにちは。瞬理です。"

台本ファイルから生成:

    shunri --file ~/Desktop/script.txt

保存先を指定:

    shunri --output ~/Desktop/shunri-reel.wav "読み上げたい文章"

標準の出力先:

    ~/shunri-voice/outputs/shunri.wav

Intel Mac では Irodori-TTS API が停止していれば `shunri` コマンドが Docker Compose サービスを自動起動します。

固定声の正本は `references/shunri.wav` です。このファイルを明示的に差し替えない限り、同じ瞬理の声を使い続けます。


## 瞬理 Reel 自動キュー

最終目標は、ChatGPT側から `@瞬理` 相当の1回の依頼で台本→瞬理音声→動画まで流すことです。

現段階では、private repository `shunpre/shun-x-scheduler` の

    runtime/shunri-reel-jobs.json

をローカルMacが監視し、`action=narrate` の確定台本を瞬理の固定声で自動ナレーション化できます。

1回だけ処理:

    make worker-once

60秒ごとの自動処理をインストール:

    make install-reel-worker

停止・削除:

    make uninstall-reel-worker

生成物:
- WAV master: `~/shunri-voice/outputs/jobs/<job-id>/narration.wav`
- downstream用MP3: private scheduler repo の `runtime/shunri-reel-assets/<job-id>/narration.mp3`

参照声 `references/shunri.wav` はローカルだけに残し、GitHubには保存しません。


## Phase 1 — Reel PoC

瞬理の確定台本から、以下を1コマンドで生成する最初の実働パイプラインです。

    確定台本
    → 瞬理の正式声
    → シーン分割
    → 日本語字幕
    → 1080x1920 MP4

最初のPoCでは人物は正準の瞬理静止画を使います。次工程でMotion Bankを接続して、参考動画のようなジェスチャー / リップシンクへ進めます。

前提:

    ~/shun-x-scheduler/assets/instagram/character/reference/canonical_front.jpeg

が存在すること。

実行:

    cd ~/shunri-voice
    git pull origin main
    make reel-poc FILE="$HOME/Desktop/script.txt"

初回のみReel renderer用Dockerイメージを自動構築します。

標準出力:

    ~/shunri-voice/outputs/reel-poc/shunri-reel-poc.mp4

途中生成物:

    ~/shunri-voice/outputs/reel-poc/.poc-work/narration.wav
    ~/shunri-voice/outputs/reel-poc/.poc-work/scene-plan.json
    ~/shunri-voice/outputs/reel-poc/.poc-work/captions.ass

設計上の重要点:
- approved scriptは書き換えない
- 音声は必ず `references/shunri.wav`
- 字幕文字はAI画像へ焼き込まずrendererが描画
- 日本語フォントはrenderer DockerにNoto CJKを入れて固定
- 1080x1920 / 30fps / H.264 + AAC


## Phase 2 — Motion Bank

Phase 1 の静止画Presenterを、瞬理専用のMotion Bankへ置き換えます。

初回:

    cd ~/shunri-voice
    git pull origin main
    make motion-bank

生成先:

    ~/shunri-voice/assets/motion-bank/

固定variant:

    neutral-talk
    open-hand
    point-up
    point-side
    think
    small-nod
    explain-both-hands
    cta-forward

現在のv1 bankは正準キャラクター画像から作る軽量モーションです。
目的はMotion Bankの選択・カット・レンダリング配線を先に完成させることです。

その後:

    make reel-poc FILE="$HOME/shunri-voice/samples/reel_script.txt"

を実行すると、scene-planごとにMotion Bank variantを自動選択し、
1枚固定ではなくPresenterカットが切り替わる縦動画を生成します。

重要:
- Motion Bankのファイル名/variant契約は今後も固定
- 後工程で同名mp4を「本物のジェスチャー動画＋lip-sync動画」に差し替える
- rendererやscene planner側は変更しない
- 旧静止画モードは --static-presenter で残す

つまり、Motion Bankの品質だけを上げればReel全体のPresenter品質も上がる構造です。


## Phase 3 — Production Motion Bank / Lip-sync adapter

本物のジェスチャー動画8本を外部で生成・撮影できたら、同じvariant名でまとめてimportできます。

    make import-motion-bank DIR="$HOME/Desktop/shunri-motion"

8本がそろうと `assets/motion-bank-production/` が自動優先されます。

さらに各sceneごとに瞬理ナレーションWAVを切り出し、lip-sync providerへ渡す段階も実装済みです。

provider未設定時:

    make reel-poc FILE="$HOME/shunri-voice/samples/reel_script.txt"

→ Motion Bankは使うがlip-syncはpassthrough。

外部lip-sync engineを接続する場合:

    export SHUNRI_LIPSYNC_COMMAND='your-command --video {video} --audio {audio} --output {output}'
    make reel-poc-lipsync FILE="$HOME/shunri-voice/samples/reel_script.txt"

詳細:

    docs/PRODUCTION_MOTION_BANK.md

Intel MacではMuseTalkのようなGPU前提OSSをローカル本番実行しない。lip-sync engineだけ外部GPUへ逃がし、音声生成・scene planning・字幕・最終renderはMac側に残す設計です。


## Phase 4 — 外部動画ツール未選定のまま進められる完成ライン

外部の動画生成 / lip-sync providerを決めなくても、現在はここまで自動化できます。

    approved script
    → 瞬理 canonical voice
    → 音声の無音区間を使った字幕タイミング補正
    → scene plan
    → Motion Bank選択
    → sceneごとの音声切り出し
    → lip-sync adapter（provider未設定時はpassthrough）
    → 任意のスクショ / 図解overlay
    → 任意BGM + narration優先のauto duck
    → 1080x1920 MP4
    → deterministic QA
    → QA合格時のみ完成扱い

標準実行:

    make reel FILE="$HOME/shunri-voice/samples/reel_script.txt"

overlayを入れる場合は、フォルダに:

    s01.png
    s03.jpg
    s05.webp

のようにscene idで置きます。

    python3 scripts/reel_poc.py       --file "$HOME/shunri-voice/samples/reel_script.txt"       --overlay-dir "$HOME/Desktop/reel-overlays"

BGMも使う場合:

    python3 scripts/reel_poc.py       --file "$HOME/shunri-voice/samples/reel_script.txt"       --overlay-dir "$HOME/Desktop/reel-overlays"       --bgm "$HOME/Desktop/bgm.mp3"

BGMはナレーションをsidechainにして自動duckします。

QA:

    outputs/.../.poc-work/qa-report.json

検査対象:
- 1080x1920
- 約30fps
- video/audio stream存在
- narration無音/空ファイル
- narration peak
- videoとnarrationの尺差
- approved script不変
- voice=shunri
- caption有無 / 重複
- 最終captionの終端
- 出力ファイルサイズ

字幕タイミングは現在、追加モデル不要の `speech-energy-pauses-v1`。
Irodoriの音声波形から無音区間を検出し、単純な文字数比例よりも句読点・間の位置へ寄せます。
将来word timestamp providerを接続した場合は、その部分だけ差し替え可能です。

### GitHub worker

local workerは今後:

    action=narrate
    action=render_reel

の両方を処理できます。

`render_reel` は軽量 review proxy、narration.mp3、scene-plan.json、captions.ass、qa-report.jsonを
private scheduler repositoryへ返します。1080x1920の完成masterはMacローカルに保持し、Git履歴を動画masterで肥大化させません。

これにより外部動画ツールを決める前でも、GitHub queueから「確定台本→完成Reel→Human Gate用レビュー」まで通せます。

## Phase 5 — worker hardening

GitHub queue → Mac worker → Reel → GitHub review proxy の往復確認後、運用耐性を追加。

### Narration headroom

Irodori出力がfull-scale付近の場合、Reel制作前にPCM WAVへ安全マージンを自動適用する。

Default target peak:

    29000 / 32767

QAは今後:
- peak = 32767 → FAIL (narration-clipping)
- peak >= 30000 → warning (narration-low-headroom)
- target peak以下 → audio headroom warningなし

これにより、今回確認された narration-near-clipping を通常運用から除去する。

### 常駐worker

一度だけ:

    make install-reel-worker

状態確認:

    make worker-status

正常なら:
- installed: yes
- launchd: loaded
- interval: 60s

となる。

以後は手動の make worker-once を原則不要にし、Macへログイン中は60秒ごとにprivate GitHub queueを確認する。

ログ:

    ~/Library/Logs/shunri-reel-worker.log
    ~/Library/Logs/shunri-reel-worker-error.log

render_reel のresultには qaWarnings も返す。

## QuickTime / macOS playback compatibility

FFmpegのH.264/AACがmetadata上は正常でも、macOS / QuickTimeの組み合わせで再生拒否される場合に備え、Apple互換copyを生成する。

既存Reelから:

    make quicktime-copy FILE="$HOME/shunri-voice/outputs/jobs/<job-id>/reel.mp4"

macOSではまず `/usr/bin/avconvert` を使い、Apple純正の720p M4Vへ変換する。
avconvertが利用できない/失敗した場合は、strict H.264 Main / level 3.1 / yuv420p / AAC-LC / CFR 30fps fallbackを使う。

GitHub workerは今後:

    local master: reel.mp4
    local QuickTime: reel-quicktime.m4v
    GitHub review: reel-review.m4v

を生成する。

QAもmetadata probeだけでなく、FFmpeg full decode testを追加し、packet/stream破損を検知する。

## Phase 6 — editorial motion / captions / auto audio

リップシンクを保留したまま、参考Reelとの差を縮めるための編集レイヤー。

### 日本語テロップ

- 最大2行
- 1行18文字を上限
- 1〜3文字だけの孤立行を禁止
- 句読点・助詞・意味境界を優先
- `ていない` / `じゃなくて` / `かもしれません` 等を途中で切らない
- 長文は1枚に詰めず、複数caption cueへ分割
- 数字 / AI / LP / Canva / CTA / CVR / CPA / 強い否定語を必要時のみサイズ強調

例:

    仕事の流れが
    変わっていないのかもしれません。

### editorial camera motion

Motion Bankの各sceneへ追加のカメラモーションを重ねる。

- slow-push
- drift-left
- punch-in
- drift-right
- micro-drift
- cta-push

静止画由来Motion Bankでも、sceneごとに寄り・左右移動・パンチインを変えて
「静止画の切替だけ」に見えにくくする。

### top overlay animation

`overlayAssets` / `--overlay-dir` の画像は、単純固定表示ではなく:

    上からスライドイン
    + fade in
    + 上部カード表示
    + scene終端でfade out

となる。実スクショ / 図解 / UIを優先。

### auto BGM / SE

外部BGM指定がない場合でも、ライセンス依存のない内部生成の低音量ambient bedを自動生成する。
SEは必要箇所だけ:

- overlay → soft pop
- punch-in → soft impact
- CTA → light click

カットごとのwhooshは使わない。
BGMは従来どおり瞬理ナレーションをsidechainにして自動duckする。

外部BGMを指定した場合は、外部BGMを優先し、auto SEだけ残す。

無効化:

    python3 scripts/reel_poc.py --file script.txt --no-auto-audio

### QA

従来QAに加え:

- 3行以上の字幕をreject
- 18文字超の行をreject
- 孤立行をreject
- 禁則文字の行頭をreject
- `ない` / `です` / `ます` / `かもし...` で不自然に始まる2行目をreject

`make self-check` はcaption / camera / auto audioのPhase-6 self-testも実行する。

## Phase 6.1 — production audio policy

Phase 6で試した内部生成のsynthetic BGM / SEは本番品質に達しないため廃止。

Production rule:
- 瞬理ナレーションは常にmaster
- BGM未指定時は narration-only
- BGMはユーザー提供 / 承認済みassetのみ使用
- BGMは0.12程度から開始し、narration sidechainでduck
- final mixは -16 LUFS / true peak -1.5 dBTP を目標
- synthetic sine / pulse / whoosh / clickは本番で自動生成しない
- SEは今後asset bank方式で追加する

外部BGMを使う場合:

    python3 scripts/reel_poc.py --file script.txt --bgm /path/to/bgm.mp3

BGMがない場合は声だけで正常に完成する。
## Phase 6.2 — caption emphasis / layout punch

Phase 6.1のproduction audio policyはそのまま維持し、見た目だけを強化する。
リップシンクは引き続き外部provider選定まで保留。

### caption color emphasis

- 基本文字は白 + 黒縁
- 重要語だけaccent colorへ変更
- accentは `config/reel_profile.json` の `captions.accentHex / accentAss` で集中管理
- default accent: `#FF7A00`
- 数字 / AI / LP / Canva / CTA / CVR / CPA / 課題語を優先

### pop emphasis

強調語はevent先頭から短時間だけ:

    100% → 115% → 100%

過剰なbounceや1文字ずつのTikTok風animationは使わない。

### fade-up entry

字幕全体は:

    下から約22px
    + 120ms fade in
    + 80ms fade out

で入る。semantic caption layout / 最大2行 / 18文字上限 / 禁則処理は継続。

### layout variants

scene planに `layoutVariant` を追加:

- `center`
- `left-presenter`
- `right-presenter`
- `fullscreen-card`

標準cycleでは、centerだけを繰り返さず、人物の左右寄せとfull-screen calloutを混ぜる。

### fullscreen card

`fullscreen-card` + overlay asset の場合は、背景の瞬理をblur/dimし、
スクショ / 図解 / UIカードを大きく中央へ入れる。
overlayがない場合でも背景処理とcallout frameで通常sceneとの差を作る。

### QA

従来QAに加え:

- ASS override brace不整合をreject
- entry animation欠落をreject
- color emphasis時のpop transform欠落をreject
- 未定義layoutVariantをreject
- full-screen calloutを含む最終video decodeを必須

`make self-check` で caption emphasis / fade-up / layout filter / QA parser を簡易検証する。

### audio

Phase 6.1のまま:

- BGM未指定 = narration-only
- BGM指定 = supplied/approved assetのみ
- synthetic BGM / SEはproductionで生成しない

## Phase 6.3 — micro captions / standalone emphasis

Phase 6.2のeditorial motion / layout punchは維持し、字幕の「理解速度」と「強調差」をさらに上げる。

### micro caption pacing

- 1 cueを最大18文字へ短縮
- 長文を1〜2行で出し続けず、意味のまとまりごとに細かく切り替える
- scene自体は増やさず、1 scene内で複数caption cueを進める
- speech-energy alignmentは維持し、cue内では文字量に応じて時間配分する

### standalone emphasis beat

以下の強い語は文章内の色替えだけで終わらせず、単独captionとして出す:

- ファーストビュー
- 仕事が減らない
- 仕事の流れ
- 数字 + 単位（例: 3時間 / 15分 / 2倍）

短い AI / LP などは原則inline emphasisのままにして、画面が騒がしくなるのを防ぐ。

standalone emphasisは通常66pxに対して約122pxを基準にし、

    100% → 125% → 110%

の短いpunchを入れる。fullscreen-cardでは126px基準。

### QA

- 旧inline color-popとPhase 6.3 standalone punchの両方を検証
- standalone cueもentry motion / fade必須
- make self-check で standalone / inline の両パターンを検証する

## Gemini Voice Design — Shunri candidates

Gemini 3.8 Flash TTSのVoice Designを、既存Irodori音声を置き換えずに比較できる。
Voice Replicationは使わない。瞬理は実在話者の声ではないため、Voice Designで新しいブランド音声を作る。

候補は `config/gemini_voice_candidates.json` に5種類:

- Shunri Core — 現行の方向に近い、低〜中域・知的・会話的
- Shunri Editorial — 低め・少しスモーキー・モード寄り
- Shunri Warm Guide — 温かく親しみやすいが甘すぎない
- Shunri Strategist — 明瞭・少し速め・戦略家の印象
- Shunri Human Texture — 微かなハスキー感・息遣い・人間味重視

APIキーはGitHubへ保存しない。Google AI StudioでAPIキーを発行してMacのTerminalにだけ設定する:

    export GEMINI_API_KEY='YOUR_KEY'

5候補をVoice Designし、同一の日本語台本で比較音声まで生成:

    make gemini-voice-candidates

出力:

    outputs/gemini-voice-candidates/

`manifest.json` に各 `voice_id` と設計promptを保存する。各候補の `*-audition.wav` は同じ台本・同じstyleで生成するので、声質の比較に使う。

既存manifestがある場合は誤って新しいstored voiceを量産しないよう停止する。作り直す場合だけ:

    python3 scripts/gemini_voice_candidates.py --force-new

Voice Designのstored voiceにはプロジェクト上限とTTLがあるため、voice_idだけではなく設計promptをcanonicalとして保持する。

### macOS Python CA fallback

Homebrew/Python環境によっては urllib が `CERTIFICATE_VERIFY_FAILED` になる。
その場合、Gemini candidate generatorはTLS検証を無効化せず、macOSの `curl` へ自動fallbackする。
APIキーはcurlのコマンドライン引数へ直接載せず、一時header file（0600）経由で渡す。

### Younger Warm Guide iteration

`Shunri Warm Guide` を基準に、少し若い声だけを比較する第2候補セットを用意する。
声質比較と速度比較を同時に混ぜすぎないため、このセットは全候補を同じ約1.2x相当のbrisk conversational styleで試聴する。

    make gemini-voice-younger-candidates

出力:

    outputs/gemini-voice-younger-candidates/

Gemini 3.8 TTSではpaceは speech_metadata.style で自然言語制御するため、約1.2xは演技指示であり厳密な再生倍率ではない。
最終候補が決まった後、必要ならFFmpeg atempoで1.2x / 1.3xの厳密な比較を行う。


## Phase 7 — parallel Remotion motion-graphics renderer

既存FFmpeg rendererは残したまま、同じ `scene-plan.json` を読むRemotion rendererを追加する。

目的:
- motion graphicsをReact componentとして再利用する
- 通常字幕 / HERO字幕 / 数字強調をcomponent化する
- presenter layout / overlay card / camera motionをframe単位で制御する
- 既存FFmpeg版と同じ入力からA/B比較できるようにする
- BGM/SE方針はPhase 6.1のまま。Remotion導入を理由にsynthetic audioを復活させない

実装はMac本体へNode/Remotionを直接入れず、Docker Linux内で行う。
Remotion公式Docker推奨構成に合わせて `node:22-bookworm-slim`、Chrome依存library、Noto CJK、Chrome Headless Shellをimageへ含める。

初回image build:

    make remotion-renderer-setup

既存の最新 `scene-plan.json` を自動検出してrender:

    make remotion-poc

work directoryを明示:

    make remotion-poc WORK="$HOME/shunri-voice/outputs/reel-poc/.poc-work"

瞬理の選択済みGemini音声など、別WAVを使ってrender:

    make remotion-poc AUDIO="$HOME/shunri-voice/outputs/gemini-voice-speed-compare/02-shunri-warm-younger-b-1p2x.wav"

`--audio` でWAVを差し替えた場合、scene timingは新しい音声尺へ比例補正して同じscene-planを使う。

標準出力:

    <work-dirの親>/shunri-reel-remotion.mp4

Phase 7 PoCでcomponent化する演出:
- PresenterScene: center / left-presenter / right-presenter / fullscreen-card
- camera: slow-push / punch-in / drift-left / drift-right / micro-drift / cta-push
- CaptionBeat: 18文字以内のmicro caption
- HERO: ファーストビュー / 仕事が減らない / 仕事の流れ / 数字+単位
- OverlayCard: screenshot / diagramのslide + fade + scale
- scene edge: short crossfade
- CTA: accent line

重要:
- Remotionは人物自体を生成したりlip-syncするengineではない
- Motion Bank / external lip-sync adapterは従来どおり別layer
- rendererの入力契約をscene-planに固定し、FFmpegとRemotionを並列維持する
- production audioはnarration-onlyまたは承認済みBGM assetのみ


## Phase 8 — Visual Director / Asset Resolver

Remotionの前に、台本の意味から「何を見せるか」を決めるVisual Directorと、
その指示をローカル素材へ結びつけるAsset Resolverを置く。

処理順:

    scene-plan.json
      → visual-director-plan.json
      → asset-resolver-plan.json
      → remotion-props.json
      → Remotion

Asset Resolver v1は外部検索や画像生成を行わない。
まず既存の承認済み素材を決定論的に解決する。

優先:
- sceneの明示 `overlay`
- `screenshot`: `overlays/` → `screenshots/` → `assets/`
- `b-roll`: `broll/` → `assets/` → `overlays/`
- scene idと同名の `s01.png` / `s02.mp4` 形式

素材が必要なのに見つからないsceneは失敗終了させず、
`assetResolution.status=missing` として記録する。
これにより後続で、画像生成・UI capture・media bankを同じcontractへ追加できる。

単体確認:

    make visual-director PLAN="/path/to/scene-plan.json"
    make asset-resolver PLAN="/path/to/visual-director-plan.json" WORK="/path/to/work-dir"

通常の `make remotion-poc` では両layerを自動実行する。
