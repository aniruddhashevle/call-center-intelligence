# Call Center Intelligence

An AI-powered call center intelligence application that transforms customer call recordings into structured, actionable insights.

The application accepts call recordings, transcribes them, analyzes the conversation, evaluates agent quality, detects compliance issues, persists the results, and generates downloadable reports.

---

## Features

### Audio Processing

- Upload or record call audio through the Gradio interface.
- Supports common audio formats including:
  - WAV
  - MP3
  - FLAC
  - M4A
- Validates uploaded audio before processing.
- Extracts audio properties such as:
  - Format
  - Sample rate
  - Number of channels
  - Frame count
  - Duration
- Rejects audio exceeding the configured maximum duration.
- Detects potentially sensitive metadata such as:
  - Phone numbers
  - Email addresses
  - Social Security numbers
  - Credit card numbers

### Speech-to-Text

- Uses `faster-whisper` for local speech transcription.
- Supports configurable Whisper model sizes.
- Uses GPU acceleration with CUDA when available.
- Falls back to CPU when GPU acceleration is unavailable.
- Uses voice activity detection to reduce unnecessary transcription.
- Produces timestamped transcription segments.
- Calculates confidence scores for transcription segments.
- Performs basic transcription cleanup.
- Provides speaker labels such as `Agent` and `Customer`.
- Uses SHA-256 audio hashing to cache previously transcribed audio.

### Call Analysis

The pipeline generates a structured call summary containing:

- Call purpose
- Key discussion points
- Resolution status
- Sentiment
- Action items
- Extracted entities

Resolution statuses include:

- Resolved
- Unresolved
- Escalated

### Quality Assurance

Calls are evaluated across configurable QA dimensions.

Each dimension contains:

- Score from 1–5
- Justification
- Compliance information where applicable

The QA system also produces:

- Overall QA score
- Dimension-level scores
- Compliance flags
- Compliance severity

Compliance severities include:

- Info
- Low
- Medium
- High

### Reports

Each completed call can produce:

- JSON report
- PDF report

Reports contain the call summary, QA results, compliance information, and transcription data.

### Persistence

The application persists processing results using SQLite and SQLAlchemy.

Stored information includes:

- Call ID
- Processing status
- Audio filename
- Transcript
- Summary
- QA scores
- Complete report
- Processing timestamp
- Trace ID

### Audit Logging

Important application actions can be written to an audit log.

Audit records contain:

- Call ID
- Action
- User
- Timestamp
- Additional details

### Observability

The application includes a Pipeline Observability dashboard with:

- Total calls
- Completed calls
- Failed calls
- Flagged / supervisor review calls
- Success rate
- Average QA score
- Compliance flag count
- Audit event count
- Recent audit events
- LangSmith configuration status

---

# Architecture

The application is organized into several layers.

```text
                         ┌─────────────────────┐
                         │     Gradio UI       │
                         │                     │
                         │  Analyze Call       │
                         │  Observability      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Pipeline Service   │
                         │                     │
                         │ process_call()      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Workflow / Graph   │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
       ┌─────────────┐      ┌──────────────┐      ┌─────────────┐
       │   Intake    │      │Transcription │      │   Summary   │
       │             │      │              │      │             │
       │ Validation  │      │ Whisper      │      │ LLM         │
       │ PII Scan    │      │ Confidence   │      │ Analysis    │
       └─────────────┘      │ Diarization  │      └──────┬──────┘
                            └──────────────┘             │
                                                        ▼
                                                 ┌─────────────┐
                                                 │     QA      │
                                                 │             │
                                                 │ Scoring     │
                                                 │ Compliance  │
                                                 └──────┬──────┘
                                                        │
                                                        ▼
                                                 ┌─────────────┐
                                                 │   Report    │
                                                 │             │
                                                 │ JSON / PDF  │
                                                 └──────┬──────┘
                                                        │
                                                        ▼
                                                 ┌─────────────┐
                                                 │   SQLite    │
                                                 │             │
                                                 │ Calls       │
                                                 │ Audit Logs  │
                                                 │ Cache       │
                                                 └─────────────┘



## System Dependencies

The application uses FFmpeg/FFprobe for audio format detection and
processing of non-WAV uploads such as MP3 and M4A.

FFmpeg must be installed on the machine running the application and
`ffmpeg` and `ffprobe` must be available on `PATH`.

### macOS

Using Homebrew:

```bash
brew install ffmpeg


## Project Structure

call-center-intelligence/
│
├── src/
│   ├── agents/
│   │   ├── intake.py
│   │   ├── transcription.py
│   │   ├── report.py
│   │   └── ...
│   │
│   ├── database/
│   │   ├── connection.py
│   │   ├── session.py
│   │   └── models.py
│   │
│   ├── graph/
│   │   ├── state.py
│   │   └── workflow.py
│   │
│   ├── security/
│   │   └── audit.py
│   │
│   ├── services/
│   │   ├── pipeline.py
│   │   └── observability.py
│   │
│   ├── ui/
│   │   ├── app.py
│   │   └── tabs/
│   │       ├── analyze.py
│   │       └── observability.py
│   │
│   └── utils/
│       ├── audio.py
│       ├── config.py
│       └── formatters.py
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── data/
│   └── app.db
│
├── .env
├── pyproject.toml
└── README.md