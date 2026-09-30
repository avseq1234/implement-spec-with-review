# implement-spec-with-review

從既有 high-level design 與 OpenSpec 規格開始，透過逐 task 的管理 subagents、外部 Codex／Claude CLI、測試證據及獨立 review 完成實作。

## 內容

- [`skills/implement-spec-with-review/SKILL.md`](skills/implement-spec-with-review/SKILL.md)：可安裝的 skill 與操作規則。
- [`scripts`](skills/implement-spec-with-review/scripts)：runner、provider adapters、測試證據捕捉、能力檢查與測試 fixture 工具。
- [`tests`](skills/implement-spec-with-review/tests)：狀態、session、review、recovery、adapter 與程序生命週期回歸測試。
- [`templates`](skills/implement-spec-with-review/templates) 與 [`references`](skills/implement-spec-with-review/references)：CLI prompts、schema、原始需求及設計決策。
- [`evidence`](evidence)：建置與實際驗證報告、測試輸出、歷次 fixture 和完整 run 紀錄。

## 安裝與使用

將 `skills/implement-spec-with-review` 目錄放入你的 Codex skills 目錄，再以 `$implement-spec-with-review` 搭配既有設計及 OpenSpec 文件啟動。先確認每次執行的 primary、reviewer、fallback model／effort、gates、有限預算與執行權限；以 [SKILL.md](skills/implement-spec-with-review/SKILL.md) 及 [runner protocol](skills/implement-spec-with-review/references/runner-protocol.md) 為準。

每個原始 task 由不同的 execution／review 管理 agent 配對處理。review 採先獨立檢查、再對照既有 findings 的兩階段流程；最多五輪。完成所有 task 後仍須通過最終整合 gate 與 review。

既有程式碼可作為修改基礎。新行為應採 test-first；若實作早於測試，保留程式、誠實記為 test-after 並繼續驗證，不會只因這項偏差停下來詢問。

## 測試

在本 repository 根目錄執行：

```sh
python3 -m unittest discover -s skills/implement-spec-with-review/tests -v
```

目前 runner 適用 POSIX/macOS 與 Git repository；程序身分與清理測試需要允許 `ps` 的 host 執行環境。外部 CLI 需要各自已設定的登入與可用模型，不能以 fake adapter 結果取代真實 provider 驗證。

## 已完成的驗證

- 回歸測試：100 次測試執行通過（包含繼承後在不同 fixture 重跑的案例，非 100 項不同需求）。
- SOL 5.6/high 從全新上下文啟動，完成兩個 task 及最終整合審查；中途額度中斷後沿用同一上下文續跑。
- 最終實際 fixture：9 個測試通過；未提供給受測 agent 的 7 個 observer 驗收測試通過。
- Codex CLI 真實驗證通過。Claude 目前僅 adapter 模擬測試，未做真實 CLI 驗證。

詳見 [原始建置報告](evidence/report.md)、[SOL 全新上下文驗證報告](evidence/sol56-fresh-context/report.md)、[最終 observer audit](evidence/sol56-fresh-context/attempt-04-observer-audit.json) 與 [最終 run summary](evidence/sol56-fresh-context/attempt-04-workspace/.spec-runs/20260930T010011+0800-2e60c700/summary.md)。這些結果對應小型合成範例；未觸發的 fallback／high-risk／五輪上限實例與 Claude 的限制均在報告中保留。

## 歷史證據的可攜性

`evidence` 是原始驗證紀錄的封存副本，包含失敗與未完成的嘗試。檔案中的絕對路徑、session ID、時間戳與雜湊保留原樣，並非新機器上的可恢復 run。原始 `/private/tmp` 或 `/Users/...` 連結不會在 GitHub 上直接開啟；請從本 repository 的 `evidence` 目錄瀏覽對應檔案。

封存不含巢狀 `.git`、Python 快取或程序 lock 檔；建立新的測試 run 請使用 skill 的 fixture 工具。完整來源對照與檔案雜湊見 [PUBLICATION_MANIFEST.json](PUBLICATION_MANIFEST.json)。
