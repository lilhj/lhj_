# Tasks: 券商研报 RAG 智能问答系统

**Input**: Design documents from `/specs/001-rag-analyst-qa/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: 核心模块测试已包含在内（Constitution Principle VIII 要求）

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/src/<module>/<file>.py`
- Tests: `backend/tests/test_<module>.py`
- Frontend: `frontend/src/components/<Component>.jsx`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, directory structure

- [ ] T001 Create full project directory structure per plan.md: `backend/src/{ingestion,chunking,embedding,indexing,retrieval,generation,api,cli}/`, `backend/tests/`, `frontend/src/components/`, `data/reports/`, `data/faiss_index/`
- [ ] T002 [P] Create `backend/requirements.txt` with dependencies: fastapi, uvicorn, python-multipart, llama-index, llama-index-vector-stores-faiss, llama-index-embeddings-huggingface, faiss-cpu, sentence-transformers, pymupdf, anthropic, python-dotenv, click, pytest, httpx
- [ ] T003 [P] Initialize frontend project: `frontend/package.json` (React + Vite), `frontend/vite.config.js`, `frontend/index.html`
- [ ] T004 [P] Create `backend/.env.example` with ANTHROPIC_API_KEY placeholder, and verify `.gitignore` covers `.env`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core RAG pipeline modules that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Implement configuration loader in `backend/src/config.py`: read ANTHROPIC_API_KEY, EMBEDDING_MODEL, CHUNK_SIZE (default 512), CHUNK_OVERLAP (default 50), TOP_K (default 3), FAISS_INDEX_DIR from environment variables with sensible defaults
- [ ] T006 [P] Implement PDF loader in `backend/src/ingestion/loader.py`: wrap LlamaIndex `SimpleDirectoryReader` with PyMuPDF backend, extract text + page numbers, return `List[Document]` with metadata `{doc_name, page_num}`
- [ ] T007 [P] Implement text splitter in `backend/src/chunking/splitter.py`: wrap LlamaIndex `SentenceSplitter` with configurable `chunk_size` and `chunk_overlap`, inject source metadata `{doc_name, brokerage, page_num, chunk_id}` into each node
- [ ] T008 [P] Implement embedder in `backend/src/embedding/embedder.py`: load BGE-large-zh via `HuggingFaceEmbedding`, expose `embed_texts(texts: list[str]) -> list[list[float]]` and `embed_query(text: str) -> list[float]`
- [ ] T009 Implement FAISS indexer in `backend/src/indexing/indexer.py`: wrap `FaissVectorStore`, methods: `build_index(nodes, embedder) -> None`, `load_index() -> VectorStoreIndex`, `persist_index() -> None`, `add_nodes(nodes) -> None`
- [ ] T010 Implement retriever in `backend/src/retrieval/retriever.py`: wrap LlamaIndex `VectorIndexRetriever` with configurable `top_k`, return `List[NodeWithScore]` with source metadata preserved
- [ ] T011 Implement generator in `backend/src/generation/generator.py`: use `anthropic` SDK to call Claude API, construct prompt with system identity (🎩 分析师助理) + context (检索片段) + question + citation requirement, return `{answer, sources[{doc, page, text, score}]}`
- [ ] T012 Create `backend/main.py`: FastAPI app entry point, mount CORS middleware (allow frontend origin), include routers from api/ module, startup event to auto-load FAISS index if exists
- [ ] T013 [P] Write unit test `backend/tests/test_loader.py`: test PDF text extraction, page count accuracy, metadata presence
- [ ] T014 [P] Write unit test `backend/tests/test_splitter.py`: test chunk count, chunk size bounds, metadata propagation
- [ ] T015 [P] Write unit test `backend/tests/test_embedder.py`: test output dimension (1024), batch vs single consistency
- [ ] T016 Write unit test `backend/tests/test_retriever.py`: test retrieval with known query, verify top_k limit, verify source metadata in results

**Checkpoint**: Foundation ready — core RAG pipeline modules tested. User story implementation can now begin.

---

## Phase 3: User Story 1 — 上传研报并建立知识库 (Priority: P1) 🎯 MVP

**Goal**: 用户通过 Web 界面或 API 上传 PDF 研报，系统自动解析并建立 FAISS 索引，
索引持久化到本地磁盘，重启后可恢复。

**Independent Test**: `curl -X POST http://localhost:8000/upload -F "files=@report.pdf"` → 201 + status "indexed"。重启后端后 `GET /status` 确认索引仍存在。

### Implementation for User Story 1

- [ ] T017 [P] [US1] Implement POST /upload route in `backend/src/api/upload.py`: accept multipart files (max 5), validate PDF type/size (100MB limit), return 201 with `{uploaded[], errors[]}`, partial success on mixed valid/invalid files
- [ ] T018 [P] [US1] Implement GET /status route in `backend/src/api/status.py`: read `data/metadata.json` + FAISS index stats, return `{indexed_docs, total_chunks, embedding_model, chunk_size, chunk_overlap, docs[]}`
- [ ] T019 [US1] Implement metadata persistence in `backend/src/indexing/indexer.py`: after successful index build, write `data/metadata.json` with doc info (id, filename, brokerage, pages, chunks, indexed_at)
- [ ] T020 [US1] Wire upload → index pipeline in `backend/src/api/upload.py`: receive files → save to `data/reports/` → call loader (T006) → call splitter (T007) → call embedder (T008) → call indexer (T009) → persist metadata (T019) → return response
- [ ] T021 [US1] Add startup index auto-load in `backend/main.py`: on app startup, check `data/faiss_index/` exists, call `indexer.load_index()`, populate global index reference for query endpoint
- [ ] T022 [P] [US1] Create FileUploader component in `frontend/src/components/FileUploader.jsx`: drag-and-drop zone + click-to-browse, file type filter (.pdf), show upload progress, display uploaded list with ✅ status
- [ ] T023 [P] [US1] Create StatusBar component in `frontend/src/components/StatusBar.jsx`: show "🎩 券商研报 RAG 问答系统" title + "已索引: N 份" badge, fetch from GET /status on mount
- [ ] T024 [US1] Create App shell in `frontend/src/App.jsx` and `frontend/src/main.jsx`: mount FileUploader (left panel) + StatusBar (top), wire API base URL config
- [ ] T025 [US1] Write integration test `backend/tests/test_api.py` (upload + status): test upload valid PDF → 201, test upload invalid file → 200 with errors[], test upload over limit → 400, test status empty → 200 with indexed_docs=0, test status after upload → shows doc

**Checkpoint**: US1 complete — 用户可通过 API 或 Web 上传研报，索引持久化，重启恢复可用。

---

## Phase 4: User Story 2 — 自然语言提问获取专业回答 (Priority: P1) 🎯 MVP

**Goal**: 用户在 Web 界面或通过 API 输入自然语言问题，系统检索 Top-K 相关片段，
调用 Claude API 生成 🎩 分析师助理口吻的专业回答，标注来源（研报名 + 页码）。

**Independent Test**: `curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d '{"question":"宁德时代产能规划"}'` → 200 + answer 包含来源标注 + sources 数组非空。

### Implementation for User Story 2

- [ ] T026 [US2] Implement POST /query route in `backend/src/api/query.py`: accept `{question, top_k?}`, validate question (1-2000 chars), check knowledge base initialized (503 if empty), call retriever (T010) → call generator (T011) → return `{answer, sources[], context_used}`
- [ ] T027 [US2] Implement "no results" handling in `backend/src/api/query.py`: when retriever returns empty or all scores below implicit threshold, return 200 with `{answer:"当前知识库中未找到相关信息", sources:[], context_used:0}`
- [ ] T028 [US2] Implement multi-turn conversation in `backend/src/api/query.py`: accept optional `conversation_id`, store recent Q&A pairs in memory (dict), inject last N exchanges into generator prompt as context
- [ ] T029 [US2] Refine generator prompt in `backend/src/generation/generator.py`: add 🎩 analyst persona system prompt ("你是某券商首席分析师助理，回答基于研报内容，必须标注来源，风格专业严谨..."), add citation format requirement ("根据《XX证券-XX研报》第X页...")
- [ ] T030 [US2] Add error handling in `backend/src/api/query.py`: Claude API timeout (30s → 502), auth failure (→ 502 generic), network error (→ 502), log detailed error to backend console
- [ ] T031 [P] [US2] Create ChatArea component in `frontend/src/components/ChatArea.jsx`: chat bubble list (user right-aligned, 🎩 left-aligned with avatar), auto-scroll to bottom, input box + send button at bottom, handle empty/loading/error states
- [ ] T032 [P] [US2] Create SourceCard component in `frontend/src/components/SourceCard.jsx`: collapsible card below each answer showing sources list — doc name, page number, excerpt text, similarity score badge
- [ ] T033 [US2] Integrate ChatArea + SourceCard into App in `frontend/src/App.jsx`: wire ChatArea to POST /query, render SourceCard below each 🎩 answer, show "请先上传研报" prompt when knowledge base empty
- [ ] T034 [US2] Write integration test `backend/tests/test_api.py` (query): test valid query → 200 with answer + sources, test empty question → 400, test overlong question → 400, test no knowledge base → 503, test irrelevant question → 200 with sources=[], test citation format present in answer

**Checkpoint**: US2 complete — 用户可以提问并获取带来源标注的专业回答。MVP 闭环。

---

## Phase 5: User Story 3 — CLI 命令行问答 (Priority: P2)

**Goal**: 分析师可在终端直接提问，CLI 调用同一套 REST API，输出与 Web 一致的
带来源标注的回答。

**Independent Test**: `python -m backend.cli query "宁德时代产能规划"` → 终端输出专业回答 + 来源列表。

### Implementation for User Story 3

- [ ] T035 [US3] Implement CLI entry point in `backend/src/cli/main.py`: use Click/Typer, subcommands `query` and `status`, call REST API at `http://localhost:8000` via `httpx`, format output with rich text (colored sources, separators)
- [ ] T036 [US3] Implement `query` command in `backend/src/cli/main.py`: accept `--question` (required) and `--top-k` (optional, default 3), POST /query, pretty-print answer with 📄 source annotations
- [ ] T037 [US3] Implement `status` command in `backend/src/cli/main.py`: GET /status, display indexed docs table (filename, pages, chunks, indexed_at)
- [ ] T038 [US3] Add CLI launcher to `backend/pyproject.toml` or document usage in README: `python -m backend.cli`

**Checkpoint**: US3 complete — CLI 可用，与 Web 共享后端。

---

## Phase 6: User Story 4 — 检索参数可调实验对比 (Priority: P3)

**Goal**: 用户在 Web 界面底部滑块调整 chunk_size (200/400/600/800) 和相似度阈值
(0.3/0.5/0.7)，重新提问后对比参数变化对回答质量的影响。

**Independent Test**: 将 chunk_size 从 512 调至 200，相似度阈值从 0.5 调至 0.7，
提问相同问题，验证检索结果数量和内容有变化。

### Implementation for User Story 4

- [ ] T039 [US4] Add parameter override support in `backend/src/api/query.py`: accept optional `chunk_size` and `similarity_threshold` in request body, pass to retriever (re-index not required — threshold filtering applied at query time)
- [ ] T040 [US4] Add threshold filtering in `backend/src/retrieval/retriever.py`: filter returned nodes by `score >= threshold` before passing to generator
- [ ] T041 [US4] Create ParameterPanel component in `frontend/src/components/ParameterPanel.jsx`: slider for chunk_size (200/400/600/800 with tick marks) + slider for threshold (0.3/0.5/0.7), send params with each query request
- [ ] T042 [US4] Integrate ParameterPanel into App in `frontend/src/App.jsx`: render at bottom of page (v1.1 slot), pass selected values to ChatArea query calls
- [ ] T043 [US4] Add parameter comparison display in `frontend/src/components/SourceCard.jsx`: show current chunk_size and threshold values alongside sources for reference

**Checkpoint**: US4 complete — 参数调节可用，可对比不同配置的检索结果。

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T044 [P] Add structured logging in `backend/src/`: each pipeline stage logs stage name, input/output summary, duration_ms; LLM calls log model, prompt_tokens, completion_tokens, latency_ms (Constitution Principle IV)
- [ ] T045 [P] Add .env validation on startup in `backend/src/config.py`: fail fast with clear error if ANTHROPIC_API_KEY missing or invalid format
- [ ] T046 [P] Add frontend error toast system in `frontend/src/`: unified error display — network timeout → "请求超时", 5xx → "服务异常", custom messages from API detail field
- [ ] T047 [P] Create `README.md` in project root: project overview, architecture diagram (ASCII), quickstart steps (link to quickstart.md), directory structure
- [ ] T048 Run through quickstart.md end-to-end validation checklist, fix any issues
- [ ] T049 Code review: verify module contracts match plan.md, verify no hardcoded secrets, verify all LLM calls logged, verify citation format in answers

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational) ⚠️ BLOCKS all user stories
    │
    ├──▶ Phase 3 (US1: Upload & Index) 🎯 MVP
    │         │
    │         ▼
    ├──▶ Phase 4 (US2: Q&A with Citations) 🎯 MVP  ← depends on US1 (needs indexed docs)
    │
    ├──▶ Phase 5 (US3: CLI)          ← depends on US2 (needs query API)
    │
    └──▶ Phase 6 (US4: Parameter Tuning) ← depends on US2 (needs query API)
                │
                ▼
          Phase 7 (Polish)
```

### User Story Dependencies

| Story | Depends On | Can Start After |
|---|---|---|
| **US1** (Upload) | Phase 2 (Foundational) | T012 complete |
| **US2** (Q&A) | Phase 2 + US1 | T020 complete (index pipeline wired) |
| **US3** (CLI) | Phase 2 + US2 | T026 complete (query API available) |
| **US4** (Params) | Phase 2 + US2 | T026 complete (query API available) |

### Within Each User Story

- API routes → after core modules (T006-T011)
- Frontend components → after API routes (can mock API for parallel dev)
- Tests → after implementation complete
- US1 MUST complete before US2 (need indexed knowledge base for meaningful Q&A testing)

### Parallel Opportunities

```
Phase 1: T002 ‖ T003 ‖ T004 (all different files)
Phase 2: T006 ‖ T007 ‖ T008 (different modules)
         T013 ‖ T014 ‖ T015 (different test files)
Phase 3: T017 ‖ T018 (different route files)
         T022 ‖ T023 (different components)
Phase 4: T031 ‖ T032 (different components)
Phase 7: T044 ‖ T045 ‖ T046 ‖ T047 (different concerns)
```

---

## Parallel Example: User Story 1

```bash
# Launch API routes in parallel:
Task: "Implement POST /upload route in backend/src/api/upload.py"
Task: "Implement GET /status route in backend/src/api/status.py"

# Launch frontend components in parallel:
Task: "Create FileUploader component in frontend/src/components/FileUploader.jsx"
Task: "Create StatusBar component in frontend/src/components/StatusBar.jsx"
```

## Parallel Example: User Story 2

```bash
# Launch frontend components in parallel:
Task: "Create ChatArea component in frontend/src/components/ChatArea.jsx"
Task: "Create SourceCard component in frontend/src/components/SourceCard.jsx"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T016) — CRITICAL GATE
3. Complete Phase 3: User Story 1 — Upload & Index (T017-T025)
4. **STOP and VALIDATE**: Test US1 independently (upload PDF, check status, restart & verify)
5. Complete Phase 4: User Story 2 — Q&A (T026-T034)
6. **MVP COMPLETE**: Test full loop — upload → ask → verify answer + citations
7. Deploy/demo if ready

### Incremental Delivery

1. Phases 1+2 → Core RAG pipeline ready
2. + US1 → Upload/index functional → **First deployable increment**
3. + US2 → Q&A with citations → **MVP! 🎉**
4. + US3 → CLI support → **v1.1 increment**
5. + US4 → Parameter tuning → **v1.1 complete**
6. + Phase 7 → Polish → **Release ready**

### Recommended MVP Scope

**Phases 1-4 (T001-T034)**: 34 tasks covering Setup → Foundational → US1 → US2.
This delivers the complete RAG loop: upload + index + Q&A with citations.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- US1 MUST complete before US2 (index needed for meaningful Q&A)
- US3 and US4 are independent of each other, both depend only on US2
- Commit after each task or logical group (2-3 tasks)
- Stop at any checkpoint to validate story independently
- Frontend components can start early with mocked API responses
