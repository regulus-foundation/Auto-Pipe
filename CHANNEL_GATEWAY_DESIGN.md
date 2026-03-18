# Auto-Pipe Channel Gateway Design -- Multi-Channel Interface

Voice commands, messenger approvals, pipeline control from anywhere.
Inspired by OpenClaw's multi-channel gateway pattern. Layer 3 design.

**Status: NOT IMPLEMENTED (Design only)**

---

## 1. Why Needed

```
Current:
  Web UI (Streamlit) is the only control tower
  -> Must always open browser
  -> Cannot trigger/approve pipeline from outside
  -> No voice commands

Goal:
  Send voice message on Telegram: "Add login feature to my-project"
  -> Pipeline runs
  -> Asks for approval via messenger
  -> Notifies when complete

  Web UI remains the control tower -- channels are remote controls
```

---

## 2. Architecture

```
+-------------------------------------------------------------------+
|                    Layer 3: Channel Gateway                         |
|                                                                    |
|  +---------+  +---------+  +---------+  +---------+               |
|  |Telegram |  | Slack   |  |Discord  |  | Web UI  |  ...          |
|  |(voice+  |  |(text)   |  |(text)   |  |(existing|               |
|  | text)   |  |         |  |         |  |  )      |               |
|  +----+----+  +----+----+  +----+----+  +----+----+               |
|       |            |            |            |                     |
|       v            v            v            v                     |
|  +-----------------------------------------------------+          |
|  |            Channel Adapter Layer                      |          |
|  |  (Per-channel message receive -> unified format)      |          |
|  +------------------------+----------------------------+          |
|                           |                                       |
|                           v                                       |
|  +-----------------------------------------------------+          |
|  |              Gateway (Event Hub)                      |          |
|  |                                                       |          |
|  |  - Message routing                                    |          |
|  |  - Intent parsing (LLM-based)                         |          |
|  |  - Session management (channel+user -> pipeline)      |          |
|  |  - Event broadcast                                    |          |
|  +------------------------+----------------------------+          |
|                           |                                       |
|                           v                                       |
|  +-----------------------------------------------------+          |
|  |              Auto-Pipe Core                           |          |
|  |  (Existing Bootstrap / Pipeline / Web UI)             |          |
|  +-----------------------------------------------------+          |
|                                                                    |
+-------------------------------------------------------------------+
```

---

## 3. Core Components

### 3.1 Channel Adapter

```python
@dataclass
class ChannelMessage:
    channel: str          # "telegram" | "slack" | "discord"
    user_id: str
    message_type: str     # "text" | "voice" | "button_action"
    content: str          # Text content (voice -> STT converted)
    raw_audio: bytes      # Original voice data (if voice)
    reply_to: str         # Reply target message ID
    timestamp: datetime
```

| Channel | Library | Voice | Priority |
|---------|---------|-------|----------|
| **Telegram** | `python-telegram-bot` | Yes (native) | **1st** |
| Slack | `slack-bolt` | No | 2nd |
| Discord | `discord.py` | No | 3rd |
| Web UI | Existing Streamlit | No | Already done |

### 3.2 Voice Pipeline

```
Telegram voice message
     |
     v
+--------------------------------------+
|  Voice Pipeline                       |
|                                       |
|  1. Receive audio (OGG/Opus)          |
|  2. STT (Speech-to-Text)             |
|     - OpenAI Whisper API (primary)    |
|     - Google STT (alternative)        |
|     - Local Whisper (offline)         |
|  3. Text -> Intent Parser             |
+--------------------------------------+
```

### 3.3 Intent Parser

| Intent | Example | Action |
|--------|---------|--------|
| `pipeline_run` | "Add login to my-project" | Trigger pipeline |
| `bootstrap_run` | "Analyze this project" | Run Bootstrap |
| `approve` | "OK", "Approve" | Human-in-the-Loop approval |
| `reject` | "Redo", "Change this" | Rejection + feedback |
| `status` | "How far along?" | Progress query |
| `cancel` | "Stop", "Cancel" | Pipeline cancellation |
| `list_projects` | "Show projects" | List registered projects |

### 3.4 Notification Policy

| Event | Notify | Reason |
|-------|--------|--------|
| Pipeline start | Yes | Start confirmation |
| Phase transition | Yes (summary only) | Progress tracking |
| **Approval request** | **Yes (required)** | **Human-in-the-Loop** |
| Build/test failure (1st) | Yes | Inform auto-fix in progress |
| Build/test retry | No | Spam prevention |
| Build/test success | Yes | Next phase notification |
| Pipeline complete | Yes | Final result |
| Pipeline failure (unrecoverable) | Yes | User intervention needed |

---

## 4. File Structure (Planned)

```
gateway/                          # Layer 3: Channel Gateway
+-- gateway.py                    # Core (routing, session, events)
+-- intent.py                     # Intent Parser (LLM-based)
+-- session.py                    # Session manager
+-- voice.py                      # Voice Pipeline (STT integration)
+-- notification.py               # Notification policy + message formatting
+-- config.py                     # Channel config (tokens, allowed users)
+-- adapters/
    +-- base.py                   # BaseAdapter abstract class
    +-- telegram.py               # Telegram bot adapter
    +-- slack.py                  # Slack bot adapter (Phase 4)
    +-- discord.py                # Discord bot adapter (Phase 4)
```

---

## 5. Implementation Roadmap

### Phase 1: Telegram Bot (MVP)
- Text commands for pipeline trigger + approval
- Basic intent parsing
- In-process async routing

### Phase 2: Voice Support
- Whisper API integration for Telegram voice messages
- Voice -> STT -> Intent -> Action

### Phase 3: Human-in-the-Loop via Channel
- Design/review approval from Telegram
- LangGraph interrupt -> Gateway approval event -> resume

### Phase 4: Multi-channel
- Slack, Discord adapters
- Same user across multiple channels (session sharing)

---

## 6. Security

| Threat | Mitigation |
|--------|------------|
| Unauthorized access | `ALLOWED_USER_IDS` allowlist per channel |
| Sensitive code leak | Channels receive summaries only, full code in Web UI only |
| API key exposure | Environment variables, never in channel messages |
| Voice recognition error | Confirmation message before execution ("Is this correct?") |

---

## 7. Web UI vs Channel Roles

```
Web UI (Control Tower)              Channel (Remote Control)
---------------------------         ---------------------------
Detailed monitoring                 Simple status query
Full code view                      Summary only
Config editing (pipeline.yaml)      No config changes
Prompt customization                Not supported
Execution history                   Not supported
Mermaid graph visualization         Not supported
Pipeline trigger                    Pipeline trigger
Human-in-the-Loop approval         Human-in-the-Loop approval
```

**Principle**: Channels handle "trigger + approve + notify" only. Detailed work in Web UI.

---

## 8. Cost Impact

| Item | Additional Cost | Notes |
|------|----------------|-------|
| Telegram bot | Free | BotFather creation |
| STT (Whisper API) | ~$0.006/min | Avg 10sec voice -> ~$0.001/call |
| Intent parsing (gpt-4o-mini) | ~$0.001/call | Short prompt |
| **Per pipeline additional** | **~$0.002** | Negligible |
