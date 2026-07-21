[English](presales-guide.md) | **繁體中文**

# 售前訪談指南（Solutions Engineer 視角）

## 口訣：量／法／接／標

| 面向 | 要問的 | 影響 |
|---|---|---|
| **量** | 峰值併發？每月音訊時數？未來成長？ | 方案與報價、rate limit 設計 |
| **法** | HIPAA/GDPR？錄音告知？聲音授權合約涵蓋 AI synthesis？ | 架構能不能上線 |
| **接** | 現有電話系統（Twilio/SIP）？CRM/ERP 怎麼接？登入身分怎麼帶？ | 整合工作量 |
| **標** | 成功指標（containment率/TTFB/成本）？誰維護 prompt 和詞庫？ | 驗收與長期維運 |

## 各場景訪談問題

### 01 文章朗讀 / 批次內容
1. 每月幾小時音訊？未來成長？→ 決定 plan 與價格
2. 有沒有專有名詞要唸對？誰維護發音詞庫？
3. QC 是人工還是自動？→ pipeline 不同
4. 發佈到哪？只是自家網站文章朗讀 → 一個 Audio Native embed 就解決，別蓋整條管線

### 02 即時串流
1. 使用者能接受的首音延遲（TTFB）目標？
2. 尖峰併發多少？→ semaphore 容量與 plan 上限

### 03 轉錄 / 跟讀
1. 真的需要 realtime 轉錄嗎？→ 80% 不需要
2. 音源品質？單人或多人？→ 拿最難樣本測 diarization
3. 錄音合規：告知、保留期限、要不要 zero retention？

### 04 配音 / 在地化
1. 目標語言與品質要求？
2. 已有腳本嗎？→ 可跳過 STT，品質更好
3. human-in-the-loop 還是全自動？→ 成本差很多
4. 原講者聲音授權談好了嗎？

### 05 語音客服 Agent
1. 現有電話系統？→ Twilio integration 或 SIP trunk
2. 峰值同時通話數？
3. 哪些情境必轉真人？轉哪支號碼？
4. 什麼能講什麼不能講？（guardrail 範圍）
5. 客戶自帶 LLM 時，延遲與幻覺的責任歸屬先講好

### 06 多角色批次
1. 角色×語言矩陣多大？聲音都在 Voice Library 授權可商用嗎？
2. 台詞量級？（10 句和 30 萬句是兩個世界）

## 坑表

| 坑 | 症狀 | 解法 |
|---|---|---|
| 429 rate limit | 批次任務大量失敗 | 指數退避 + queue 控併發 + 記 xi-request-id |
| 用舊模型 | scribe_v1 呼叫失敗 | 已於 2026/7 移除，遷 scribe_v2 |
| 前端信任問題 | 使用者偽造 override 提權 | 後端 tool 各自驗證，agent trust_context 設 low |
| Tool 慢 | 對話中尷尬沉默 | pre-tool speech + soft timeout filler |
| 幻覺報價/政策 | Agent 講了 KB 沒有的內容 | prompt 明定拒答 + source_attribution + evals 回歸測試 |
| 成本爆炸 | 月底 credit 用罄 | 預算×1.75、監控 overage、分場景用便宜模型 |
| 聲音授權 | 上線後法務叫停 | 訪談期就問授權鏈，PoC 用 Library/Design 聲音 |
| 沒有測試集 | 每次改 prompt 都靠感覺 | 用平台內建 Tests/Evals，改動必跑回歸 |

## RAG 知識庫要點
- KB 在哪？多久更新？誰更新？指定文件要有 owner 與更新頻率（agent 講舊價格就是這樣來的）
- 大 KB 用 RAG，system prompt 只放一千字內
- 平台內建 KB 省掉外部 embedding pipeline，除非客戶已有成熟平台
- 打不出來多半是文件品質問題，不是 LLM 問題
- 不同客戶不同報價 → 用 tools + auth query，不要塞 KB

## Multi-agent 拆分原則
- Prompt 越長遵循度越差、延遲高、難測試 → 拆 sub agent：prompt 短、工具少、KB 小、行為可預測
- 但**工具集或知識庫明顯不同時才拆節點**，不要為拆而拆
- Router agent 只做意圖分類，不確定就問
- 每個節點可各自 override 音色/LLM/tools；每個節點的 prompt 要有 owner
