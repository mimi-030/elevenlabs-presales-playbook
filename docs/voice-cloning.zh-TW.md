[English](voice-cloning.md) | **繁體中文**

# Voice Cloning 決策指南

```
需要特定真人的聲音嗎？
├─ NO  → Voice Design 或 Voice Library（最快，PoC 首選）
└─ YES → 品質要求？
    ├─ 高       → PVC 專業級聲音克隆：30 min 錄音，3–6 hr 排隊訓練
    └─ 低/快驗證 → IVC 即時聲音克隆：1–5 min 錄音
```

## 先問法務再動手

1. **代言人授權聲音合約有沒有涵蓋 AI synthesis？合約多久？**
   上線後被法務叫停是真實案例——訪談期就要問授權鏈。
2. **需要 brand voice alignment 嗎？**
   同一個 voice_id 貫穿所有 call agent、廣告、App，品牌聲音才一致。

## 實務建議

- PoC 階段一律用 Voice Library（授權可商用）或 Voice Design，別等 PVC 訓練
- 固定 voice_id 和 seed，輸出才可重現（場景 6 的 registry 就是為此存在）
- 授權快到期的聲音要有下架與替換流程（registry 讓你一鍵換 voice_id）
