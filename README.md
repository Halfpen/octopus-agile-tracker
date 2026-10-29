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
