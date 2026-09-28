# AGENTS.md

このファイルは現在の `shunri-voice` 開発における最上位ルールである。
将来のRepository名は `shunapps_creative` を予定する。

## ShunApps Platform Common Rules

このRepositoryはShunApps Platformの独立Domainである。

最上位原則:

> 裏側は独立、表側は1つ。

> Engineは作る。JEVは判断する。Orchestratorはつなぐ。

### Common responsibility rules

- Domainは自分のBusiness Logic / Data / Credentialを所有する
- 他Domainの内部実装を直接取り込まない
- Cross-domain通信はAPI / Webhook / Event / Job / Artifact Contractで行う
- JEVはDecision / Quality GateでありWorkflow Engineではない
- Orchestratorは順序 / Wait / Retry / Timeout / Branch / Human Gate / Notificationを担当する
- OrchestratorへDomainのSource of Truthを置かない
- 各DomainはOrchestratorなしでも単独実行可能にする
- Human Gateを越えて勝手に外部公開・送信・投稿しない
- PIIを不要にCross-domain payloadへ複製しない
- Repository / Backendが別でも、ユーザー向けUIはV2 Design Systemへ統一する
- Option独自のAccount / Navigation / Design Systemを作らない
- 各Optionは決済Providerを直接扱わず、Entitlementのみ参照する

Common Contractの概念:
- Job = 作業要求
- Event = 発生した事実
- Artifact = 完成成果物
- Decision = PASS / REVISE / HUMAN / FAIL

Envelopeは原則:
- schemaVersion
- tenantId
- correlationId
- createdAt
- idempotencyKey（必要な場合）
- domain payload / artifact reference

専用 `shunapps_platform` Repository作成までは、
`shunapps_lp_v2/docs/platform/` と `shunapps_lp_v2/contracts/` をPlatform暫定正本とする。


## Creative Domain Canonical Responsibility

このRepositoryは今後 **Creative Engine** の原型として育てる。

担当:
- image generation
- video generation
- Reel / carousel / banner / thumbnail生成
- audio / narration（Creative制作に必要な範囲）
- Remotion / renderer
- motion bank
- caption rendering
- Visual Director
- Asset Resolver
- Creative QA
- Creative Artifact生成

担当しない:
- SNS OAuth
- SNS予約
- SNS publish
- SNS投稿結果のSource of Truth
- 広告配信実行
- Billing
- Orchestration engineそのもの

Creativeは「作ってArtifactを返して終了」する。
次にどこへ投稿するかをCreative自身が決めない。

## Current development status

**Creative開発は継続してよい。**

ただし今後の新規実装は、Scheduler内部に処理を増やすのではなく、
このCreative Domain側へ集約する。

Schedulerとの既存queue / runtime連携は移行経路として扱う。
Common Contract + Orchestrator経路が完成するまで壊さない。

## Output rule

生成結果は明示的なArtifactとして返す。

例:
- creative.image
- creative.video
- creative.reel
- creative.audio
- creative.caption_track

Artifactはversion / status / correlationIdを追跡可能にする。

## Human Gate

Creative生成完了だけではSNS投稿・広告反映・外部公開を許可しない。
JEV / Human Gate / 実行Domainの責務を越えない。

## UI

ShunLP Platform内でCreative UIを提供する場合、V2 Design Systemへ統一する。
独自の別製品風Navigation / Account体験を作らない。

## Repository migration

Creative責務が安定した後、`shunri-voice` → `shunapps_creative` へ整理する。
音声専用Repositoryという旧名称に引っ張られて責務を狭めない。
