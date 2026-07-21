[English](README.md) | **繁體中文**

# ElevenLabs 售前實戰手冊

**怎麼跑一場語音 AI 專案的 discovery call —— 以及六個可直接執行的 PoC，
用來回答那場對話裡冒出來的問題。**

語音 AI 專案很少死在 API 上。它們死在沒人問過尖峰併發多少、這個聲音是誰的、
發音字典上線後誰維護——而這些問題往往等到架構都畫完了才浮出來。

這個 repo 是互相依賴的兩半：

1. **[訪談指南](docs/presales-guide.zh-TW.md)**——各情境該問客戶什麼，
   歸納成四個面向：Volume（量）、Legal（法）、Integration（接）、Metrics（標）。
   另外附上踩坑對照表：我們遇過的失敗模式、症狀、修法。
2. **六個 PoC**——一個模式一個，全部**不需要 API key 就能跑**，
   所以客戶說「可以看一下嗎」的時候，你兩分鐘內就能把東西放上螢幕。

從 Solutions Engineer 的視角寫成：先問對問題，再畫架構。

> 註：專案的程式碼、註解與介面一律使用英文，只有 `README.zh-TW.md` 系列提供中文。

## 從這裡開始

| 你現在的處境 | 去哪裡 |
|---|---|
| 準備一場 discovery call | [docs/presales-guide.zh-TW.md](docs/presales-guide.zh-TW.md) |
| 要決定即時還是批次、用哪個產品 | 下方的[怎麼選技術路線](#怎麼選技術路線) |
| 要決定用哪個聲音、能不能複製 | [docs/voice-cloning.zh-TW.md](docs/voice-cloning.zh-TW.md) |
| 兩分鐘內要生出一個 demo | 下方的[快速開始](#快速開始) |

```
elevenlabs-production-patterns/
├── docs/
│   ├── presales-guide.md  各情境訪談問題 + 踩坑對照表
│   ├── voice-cloning.md   PVC / IVC / Voice Design 決策指南
│   ├── diagrams/          架構圖與決策圖
│   └── screenshots/       每個 demo 跑起來長什麼樣
├── 01-tts-cache/          發布時生成 + 內容指紋 cache
├── 02-stream-safeclient/  逐句串流 + 併發閘門與重試
├── 03-readalong-player/   STT 對齊 + 無狀態二分搜尋高亮
├── 04-dubbing-workflow/   審核狀態機 + 樂觀鎖 + 審計簿
├── 05-voice-agent/        Agents widget + 後端驗證身分的 webhook
└── 06-batch-registry/     聲音對照表 + manifest 驅動、可重試的批次
```

## 長什麼樣子

<table>
<tr>
<td width="50%"><img src="docs/screenshots/5001.png" alt="語音管理後台"><br><sub><b>01</b> 發布時生成 + 內容指紋 cache</sub></td>
<td width="50%"><img src="docs/screenshots/5002.png" alt="延遲實驗室"><br><sub><b>02</b> 實測 TTFB 對比與 429 壓力測試</sub></td>
</tr>
<tr>
<td><img src="docs/screenshots/5004.png" alt="配音審核看板"><br><sub><b>04</b> 帶審計簿的審核狀態機</sub></td>
<td><img src="docs/screenshots/5006.png" alt="批次控制台"><br><sub><b>06</b> 聲音對照表與 manifest 驅動的重試</sub></td>
</tr>
</table>

## 適合誰讀

需要坐在客戶對面、把一個語音 AI 專案 scope 出來的 Solutions Engineer、架構師與售前技術人員——
也就是「API 會不會動」已經不是問題，真正要回答的是成本、延遲、併發、審核流程與聲音授權的階段。

反過來看也成立：如果你是客戶，這些正是一個稱職的廠商應該問你的問題。

**執行時間**：任一情境約兩分鐘，不需要 API key，也不需要帳號。

## Discovery 的四個問題

照這個順序問。每一個都可能直接推翻你正打算畫的架構。

| | 問什麼 | 這個答案決定了 |
|---|---|---|
| **Volume（量）** | 尖峰併發、每月音訊時數、成長曲線 | 方案與定價，以及需不需要做 rate limit 策略 |
| **Legal（法）** | 法遵要求、錄音告知、聲音合約有沒有涵蓋 AI 合成 | 這件事到底能不能上線 |
| **Integration（接）** | 既有電話系統、怎麼接到 CRM/ERP、身分怎麼帶進來 | 實際上大部分的工程量 |
| **Metrics（標）** | 成功標準，以及上線後誰維護 prompt 與字典 | 驗收條件，以及半年後還活不活著 |

各情境的完整訪談問題與踩坑對照表：
**[docs/presales-guide.zh-TW.md](docs/presales-guide.zh-TW.md)**。

## 六個情境

每一個都對應一場往某個方向發展的客戶對話。

| # | 情境 | 問題 | 修法 | 結果 |
|---|------|------|------|------|
| [01](01-tts-cache/) | 新聞文章語音化 | 每位讀者瀏覽都重新生成，帳單翻倍 | 在「發布時」生成，用內容指紋做 cache | 生成一次，服務百萬次播放 |
| [02](02-stream-safeclient/) | 延遲與速率限制 | 開口前先沉默 4 秒；尖峰時段爆 429 | 逐句串流；併發閘門加上帶 jitter 的 backoff | TTFB 3.6 秒降到 0.9 秒，使用者看不到錯誤 |
| [03](03-readalong-player/) | 跟讀播放器 | 使用者一拖進度條，高亮就跑掉 | 離線對齊一次，每個 tick 做無狀態二分搜尋 | 任意播放位置都正確，O(log N) |
| [04](04-dubbing-workflow/) | 配音審核看板 | 多人同時編輯互相覆蓋；核可後又被改 | 狀態機加樂觀鎖加審計簿 | 非法動作直接擋下，沒有東西被默默蓋掉 |
| [05](05-voice-agent/) | 電商語音客服 | Agent 需要查訂單，但不該被信任 | webhook 中介層在後端驗證身分 | 安全地查訂單並轉真人 |
| [06](06-batch-registry/) | 遊戲台詞批次生成 | 一句壞掉，30 萬句的批次一起陪葬 | 聲音對照表加 manifest 驅動的批次器 | 只重跑失敗的那幾句 |

Port 與資料夾編號一致：情境 `NN` 跑在 port `50NN`。

## 快速開始

每個情境都是獨立的：

```bash
cd 01-tts-cache        # 或任何其他情境
pip install -r requirements.txt
python app.py          # 情境 01 -> http://localhost:5001
```

**預設是 MOCK 模式。** 沒有 API key 時，情境會跑在模擬後端上：零成本、行為可重現、
而且完整走過整條流程。建議先在這裡把問題的形狀看清楚。

**REAL 模式**會真的呼叫 API：

```bash
cp .env.example .env   # 填入 ELEVEN_KEY 後重啟
```

MOCK 模式的數字來自模擬後端。它們是確定性的，適合用來說明修法的形狀，
但**不是** ElevenLabs API 的效能基準——想要屬於你自己網路與帳號的數字，請跑 REAL 模式。

## 怎麼選技術路線

**有人正在等這段語音嗎？**

- 有，即時：TTS 用 `flash_v2_5` 或 `v3_conversational`，STT 用 `scribe_v2_realtime`，
  LLM 優先選小而快的。
- 沒有，批次：TTS 用 `multilingual_v2` 或 `v3` 換品質，STT 用 `scribe_v2` 批次
  （更便宜、功能更完整），再用佇列控制併發、用 backoff 處理重試。

**這是什麼類型的問題？**

- 即時對話 → ElevenLabs Agents（情境 05）
- 大量內容生產 → 批次管線（情境 01、06）
- 理解既有音訊 → Scribe（情境 03）
- 該用哪個聲音 → [語音複製決策指南](docs/voice-cloning.zh-TW.md)

## 架構圖

情境架構圖與 pre-sales 決策圖都放在 [docs/diagrams/](docs/diagrams/)，
並附有一份索引說明每張圖的用途。

這些圖以中文標註，所以只在中文版 README 內嵌顯示；英文版改成連結，
避免英文讀者一打開就看到滿版中文。各情境的架構圖在該情境的 `README.zh-TW.md` 底部。

## 這個專案不是什麼

這些是 PoC，每一個只為了把一個概念講清楚。它們沒有身分驗證、用 JSON 檔而不是資料庫存狀態、
跑在 Flask 開發伺服器上。可以直接借走的是那些模式，不是這些管線本身。

## 授權

[MIT](LICENSE)
