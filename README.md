# Agile 電費追蹤

追蹤 Octopus Energy **Agile** 電價同燃氣嘅本期帳單，數據直接由瀏覽器向 Octopus 官方 API 讀取。

- 今日 / 明日每半小時電價、最平連續 2 小時、負電價時段（公開數據，唔使 API key）
- 本期累計帳單（電 + 燃氣，包括 standing charge 同 VAT）同全期推算
- 每日費用圖，撳入去睇半小時用電同電價
- 你嘅加權電均價對比同期 Agile 簡單平均

## 用法
打開網頁，輸入 Octopus API key（Account → Personal details → API access）同帳戶號碼。
設定只會存喺你自己瀏覽器嘅 localStorage，唔會傳去 Octopus 以外嘅地方。

## 限制
- 智能電錶數據一般遲大約一日先上到 API
- 未計 Saving Sessions / Weekend Happy Hour 等 credit

## 平電通知（ntfy）
`.github/workflows/agile-notify.yml` 每日喺 Octopus 公佈明日電價後執行，計出低過門檻嘅時段，
透過 [ntfy](https://ntfy.sh) 預先排定推送：即時一條明日總結，另外每段平電開始前幾分鐘再推一條。

設定：
1. 手機裝 ntfy app，訂閱一個難估嘅 topic 名（topic 名就等於密碼）
2. Repo Settings → Secrets and variables → Actions → **Secrets** 加 `NTFY_TOPIC`
3. （可選）**Variables**：`THRESHOLD`（p/kWh 含VAT，預設 10）、`LEAD_MIN`（提前幾多分鐘，預設 5）、
   `VAT_PERCENT`（預設 0）、`TARIFF`（預設 `E-1R-AGILE-24-10-01-G`）、
   `CHARGE_HOURS`（Tesla 充電要幾多個鐘，預設 4）、`SUPERCHARGER_P`（附近超充站每 kWh 價錢，預設 25）
4. Actions → Agile cheap-price notifications → Run workflow → `test`，測試收唔收到
