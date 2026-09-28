# 🧠 PROJECT MINDMAP — Alert Aggregation in Microservices

> ⚠️ **CẢNH BÁO TÍNH MỚI (cập nhật 2026-09-28)**: mindmap này được tạo **trước khi kiểm chứng dữ liệu RCAEval**, nên một số số liệu đã **lỗi thời**. Các điểm cần bỏ qua:
> - "735 failure cases" → thực tế chỉ **359 case có log** (suite RE1 gồm 375 case là metric-only).
> - "WARNING-level logs only" → RCAEval **không có cột `severity`**; mức phải **tự gán** theo quy trình 3 tầng.
> - "Log + Metric + Trace" cho mọi case → chỉ **240 case có trace**, **8 case có `root_cause.txt`**.
> - "ARR ≥ 50%" ở phần Metrics và "≥ 60%" ở phần TÓM TẮT → **mâu thuẫn**; giá trị đã chốt là **≥ 60%**.
> - "Group Purity" cho RCPR → RCPR nay có **định nghĩa kép** (mức service và mức alert).
>
> **Nguồn đúng cần dùng**: `cp1/data_schema_notes.md` (số liệu kiểm chứng), `cp1/CP1_Ban_Dinh_Huong.md` (định hướng đã sửa), `cp2/CP2_Gap_Analysis.md` (gap analysis).

> Auto-generated from project analysis

---

## 1. HIGH-LEVEL OVERVIEW (Sơ đồ tổng thể)

```mermaid
mindmap
  root((🎯 Alert Aggregation<br/>Microservices))
    📋 Scope
      WARNING-level logs only
      Microservices architecture
      8-week timeline
      2h/day research
    📊 Dataset
      RCAEval ✅ Primary
        735 failure cases
        3 systems: Online Boutique, Sock Shop, Train Ticket
        Log + Metric + Trace + Root Cause Label
        MIT License
      LEMMA-RCA 🔄 Backup
        CC-BY-NC-4.0
        Log + Metric (no Trace)
        DDoS, storage failure, resource contention, noisy neighbor
    🧪 Methodology (4 Arms)
      Arm 1: Rule-based (Prometheus Alertmanager)
      Arm 2: Semantic Similarity (S-BERT + DBSCAN)
      Arm 3: Temporal-Spatial (Topology Graph)
      Arm 4: LLM Agent Tool-calling
    📏 Metrics
      ARR ≥ 50%
      RCPR ≥ 95%
      Group Purity
      Pairwise F1-Score
    🎯 Novelty
      WARNING-level focus
      Pre-failure / Early warning
      Agent tool-calling approach
```

---

## 2. PROJECT FLOW & CHECKPOINTS

```mermaid
graph TD
    subgraph "Tuần 1 — CP1"
        A1[Chốt dataset] --> A2[Định nghĩa Noisy Alert Warning]
        A2 --> A3[Research Question + Hypothesis]
        A3 --> A4[Bản định hướng 1 trang → Gửi thầy Long]
    end

    subgraph "Tuần 2 — CP2"
        B1[Đọc COLA, AlertGuardian] --> B2[Gap Analysis 1 trang]
        B2 --> B3[Chốt Research Gap]
        B3 --> B4[Chốt Baseline + Metric + Design]
        B4 --> B5[Gửi CP2 → Thầy Long]
    end

    subgraph "Tuần 3 — CP3/CP4"
        C1[Parse RCAEval dataset] --> C2[Filter WARNING logs]
        C2 --> C3[Tạo Alert Stream CSV/JSON]
        C3 --> C4[Test sample + ghi nhận vấn đề]
        C4 --> C5{RCAEval ổn?}
        C5 -->|Yes| C6[OK - tiếp tục]
        C5 -->|No - quá 1 buổi| C7[Switch sang LEMMA-RCA]
    end

    subgraph "Tuần 4 — CP4b + CP5"
        D1[Build MVP Agent] --> D2[Tool: get_related_alerts]
        D2 --> D3[Tool: get_service_dependency]
        D3 --> D4[Baseline rule-based]
        D4 --> D5[Service dependency table static]
        D5 --> D6[Synthetic runbook cho fault types]
    end

    subgraph "Tuần 5 — CP5 (full)"
        E1[Run agent trên toàn bộ alert stream] --> E2[So sánh vs baseline]
        E2 --> E3[Bảng ARR, RCPR, Purity]
        E3 --> E4[Phân tích failure cases]
        E4 --> E5{Tool 3 cần thêm?}
        E5 -->|Yes| E6[Add get_runbook - synthetic only]
        E5 -->|No| E7[Báo cáo với 2 tools]
    end

    subgraph "Tuần 6 — CP6 + CP7 + CP8"
        F1[Viết Methodology + Related Work] --> F2[Viết Results + Discussion]
        F2 --> F3[Viết Limitations + Conclusion]
        F3 --> F4[Gửi bản nháp → Thầy Long]
        F4 --> F5[Buffer: test + sửa failure cases]
        F5 --> F6[Nộp bản cuối]
    end

    A4 --> B1
    B5 --> C1
    C6 --> D1
    C7 --> D1
    D6 --> E1
    E7 --> F1
    E6 --> F1
```

---

## 3. NOISY ALERT CLASSIFICATION

```mermaid
graph LR
    subgraph "4 loại Noisy Alert Warning"
        N1[🔴 Duplicate<br/>Cùng root cause<br/>cùng time window]
        N2[🟡 Transient<br/>Tự biến mất<br/>không cần can thiệp]
        N3[🟠 Unactionable<br/>Đúng kỹ thuật<br/>nhưng không có SOP]
        N4[🔵 Cascading<br/>Downstream effect<br/>của root cause khác]
    end

    N1 --> OUT[Nguyên nhân: Thiếu deduplication]
    N2 --> OUT2[Nguyên nhân: Threshold quá nhạy]
    N3 --> OUT3[Nguyên nhân: Alert design kém]
    N4 --> OUT4[Nguyên nhân: Topology-blind]

    OUT --> SOL[Giải pháp: Alert Aggregation]
    OUT2 --> SOL
    OUT3 --> SOL
    OUT4 --> SOL
```

---

## 4. METHODOLOGY COMPARISON

```mermaid
graph TB
    subgraph "4 Arms — So sánh phương pháp"
        direction TB

        subgraph "Arm 1: Rule-based"
            R1[Prometheus Alertmanager]
            R2[group_by: service + alertname + severity]
            R3[group_wait=30s, group_interval=5m]
            R4[❌ Topology-blind]
        end

        subgraph "Arm 2: Semantic Similarity"
            S1[Drain3 → Log Template]
            S2[Sentence-BERT → 384d vector]
            S3[DBSCAN / HDBSCAN clustering]
            S4[❌ Causality-blind]
        end

        subgraph "Arm 3: Temporal-Spatial"
            T1[Service Topology / Call Graph]
            T2[Ma trận kề Caller-Callee]
            T3[Sliding window Δt: 30s/60s/120s]
            T4[❌ Time-sensitive noise]
        end

        subgraph "Arm 4: LLM Agent"
            L1[Fast Filter: Dedup + Time-window]
            L2[LLM Reasoning: GPT-4o-mini / DeepSeek]
            L3[Chain-of-Thought + Runbook]
            L4[❌ High latency & token cost]
        end
    end

    R1 --> COMP[📊 So sánh trên cùng dataset]
    S1 --> COMP
    T1 --> COMP
    L1 --> COMP

    COMP --> METRICS[ARR + RCPR + F1 + Purity + Latency]
```

---

## 5. DATASET SCHEMA MAPPING

```mermaid
graph LR
    subgraph "RCAEval Fields"
        F1[case]
        F2[root_cause_service]
        F3[fault + fault_description]
        F4[n_logs + has_logs]
        F5[normal_timesteps]
        F6[faulty_timesteps]
        F7[inject_time]
        F8[system]
    end

    subgraph "Noisy Alert Mapping"
        M1[Root Cause Label → RCPR ground truth]
        M2[Fault Type → Service gốc]
        M3[Log Source → Sinh alert warning]
        M4[Normal Period → Noisy nếu alert ở đây]
        M5[Faulty Period → Signal/Cascading]
        M6[Time Window → Aggregation window]
        M7[Topology → Dependency table]
    end

    F1 --> M1
    F2 --> M1
    F3 --> M2
    F4 --> M3
    F5 --> M4
    F6 --> M5
    F7 --> M6
    F8 --> M7
```

---

## 6. ALERT PIPELINE

```mermaid
graph LR
    subgraph "Step 1: Load"
        P1[Load cases<br/>has_logs=True<br/>từ RCAEval]
    end

    subgraph "Step 2: Parse"
        P2[Parse log entries<br/>Extract level=WARNING]
    end

    subgraph "Step 3: Create Alert Object"
        P3["{alert_id, service,<br/>timestamp, message_template,<br/>severity='warning'}"]
    end

    subgraph "Step 4: Label"
        P4{Timestamp<br/>ở đâu?}
        P4 -->|normal_timesteps| P5[Label: noisy<br/>transient]
        P4 -->|faulty + root_cause_service| P6[Label: signal]
        P4 -->|faulty + khác service| P7[Label: cascading/noisy]
    end

    subgraph "Step 5: Aggregate"
        P8[Apply aggregation<br/>→ Measure ARR + RCPR]
    end

    P1 --> P2 --> P3 --> P4
    P5 --> P8
    P6 --> P8
    P7 --> P8
```

---

## 7. AGENT ARCHITECTURE

```mermaid
graph TB
    subgraph "MVP Agent (Tuần 4-5)"
        AGENT[AI Agent<br/>LLM: GPT-4o-mini / DeepSeek-V3]

        TOOL1["🔧 Tool 1:<br/>get_related_alerts<br/>(service, time_window)"]
        TOOL2["🔧 Tool 2:<br/>get_service_dependency<br/>(service)"]
        TOOL3["🔧 Tool 3:<br/>get_runbook<br/>(fault_type)<br/>— Synthetic only!"]

        AGENT -->|max 2 tool calls / decision| TOOL1
        AGENT --> TOOL2
        AGENT -->|optional, nếu còn thời gian| TOOL3

        TOOL1 --> DECISION[Quyết định gom nhóm]
        TOOL2 --> DECISION
        TOOL3 --> DECISION

        DECISION --> OUTPUT[Consolidated Incident Ticket]
    end

    subgraph "Baseline"
        BASE1[Rule-based: service + severity + time_window]
        BASE2[Time-window only: gom tất cả trong window]
        BASE3[No aggregation: ARR = 0%]
    end

    OUTPUT --> COMPARE[📊 So sánh với Baseline]
    BASE1 --> COMPARE
    BASE2 --> COMPARE
    BASE3 --> COMPARE
```

---

## 8. RESEARCH GAP ANALYSIS

```mermaid
graph TB
    subgraph "Current Literature"
        L1[Post-failure RCA<br/>❌ Sau khi sập rồi mới phân tích]
        L2[Rule-based<br/>❌ Topology-blind]
        L3[Semantic Similarity<br/>❌ Causality-blind]
        L4[Temporal-Spatial<br/>❌ Time-sensitive]
        L5[LLM-based<br/>❌ High cost/latency]
    end

    subgraph "3 Gaps Identified"
        GAP1["Gap 1: WARNING-level<br/>chưa được nghiên cứu<br/>độc lập"]
        GAP2["Gap 2: Không phương pháp nào<br/>kết hợp được topology<br/>+ semantic + agent"]
        GAP3["Gap 3: Thiếu benchmark<br/>+ metric đa chiều<br/>cho early-warning"]
    end

    L1 --> GAP1
    L2 --> GAP2
    L3 --> GAP2
    L4 --> GAP2
    L5 --> GAP2

    GAP1 --> SOLUTION["🎯 Đề tài: Agent Tool-calling<br/>trên WARNING-level logs<br/>với ARR + RCPR + F1 metrics"]
    GAP2 --> SOLUTION
    GAP3 --> SOLUTION
```

---

## 9. FACT-CHECK STATUS

```mermaid
pie title "Fact-Check Status — Why.md"
    "✅ Đúng hoàn toàn" : 6
    "⚠️ Chưa xác minh đầy đủ" : 4
    "❌ Thiếu Reference" : 1
```

---

## 10. KEY REFERENCES

```mermaid
graph LR
    subgraph "Core Papers"
        COLA["COLA<br/>ICSE-SEIP 2024<br/>arXiv:2403.06485<br/>F1: 0.901-0.930"]
        AG["AlertGuardian<br/>ASE 2025<br/>arXiv:2601.14912<br/>ARR: 94.8%"]
        RCA["RCAEval<br/>WWW 2025<br/>arXiv:2412.17015<br/>735 cases"]
    end

    subgraph "Industry Reports"
        PD["PagerDuty 2020/2026"]
        GR["Grafana Labs 2025"]
        NR["New Relic 2026"]
        MS["Microsoft/Omdia 2026"]
    end

    subgraph "Foundational"
        SRE["Google SRE Book<br/>Ch.6 + Ch.10 + Ch.11"]
        PROM["Prometheus Alertmanager<br/>Rule-based baseline"]
    end

    COLA --> THIS[📌 This Research]
    AG --> THIS
    RCA --> THIS
    SRE --> THIS
    PROM --> THIS
```

---

## 📌 TÓM TẮT DỰ ÁN (1 slide)

| Thành phần | Chi tiết |
|---|---|
| **Tên đề tài** | Alert Aggregation từ Log WARNING để giảm Noisy Alerts trong Microservices |
| **Novelty** | WARNING-level (pre-failure) + Agent tool-calling |
| **Dataset chính** | RCAEval — 735 cases, 3 microservice, MIT license |
| **4 phương pháp** | Rule-based → Semantic → Temporal-Spatial → LLM Agent |
| **Metric chính** | ARR ≥ 50%, RCPR ≥ 95% |
| **Agent tools** | `get_related_alerts` + `get_service_dependency` (+ optional `get_runbook`) |
| **Baseline** | Prometheus Alertmanager, Time-window only, No aggregation |
| **Timeline** | 8 tuần, 2h/ngày |
| **Giáo viên hướng dẫn** | Thầy Long |