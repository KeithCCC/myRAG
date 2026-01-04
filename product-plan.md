了解どすえ🧠✨ Codexにそのまま貼れるように、**要件・画面・機能・データモデル・実装順**を一枚にまとめますえ。
（※コードは入れず、指示として完結する形にしてます）（ゆかり）

---

## Codex向けサマリー：ローカルRAG「Folder RAG」MVP

### 目的

PC上で動く**ローカルRAGアプリ**を作る。ユーザーが指定したフォルダ内のファイル（まず `pdf/txt/md`）をインデックス化し、**キーワード検索（全文）＋意味検索（Embedding）**と、**引用（根拠）つき回答**を提供する。Everything連携はしない（後回し）。

---

## MVPスコープ

### Must（必須）

1. **フォルダ取り込み**

* ユーザーがフォルダを追加
* 対象拡張子は MVP では固定：`pdf`, `txt`, `md`
* 追加後に「インデックス作成」を実行（手動）

2. **インデックス作成パイプライン**

* フォルダ走査 → ファイル一覧
* テキスト抽出（PDFはページ番号を保持）
* チャンク化（500〜1000 token相当）
* Embedding生成（ローカル）
* ローカル保存（SQLite + ベクトル索引）
* 進捗表示（total/done/error_count）＋エラー一覧

3. **検索**

* **全文検索**：SQLite FTS5
* **意味検索**：ベクトル近傍（MVPは FAISS で別indexファイルでもOK）
* 結果は「根拠カード」形式で表示：doc名 / ページ（PDF） / スニペット / スコア

4. **質問（RAG回答）**

* 質問→検索（TopK chunks）→短い回答を生成
* 必ず根拠（引用）を併記：doc名＋ページ＋スニペット
* MVPでは生成を2モードにしてよい：

  * 生成なし：根拠カードの要点整形（LLM不要）
  * 生成あり：ローカルLLMまたは外部LLM（どちらか一つを選択）

### Not in MVP（後回し）

* OCR（スキャンPDF）
* docx/pptx等の追加形式
* 自動ファイル監視（まず手動再インデックス）
* クラウド同期・共有・マルチ端末

---

## UI（3画面）

1. **Library（フォルダ管理）**

* 追加/削除
* インデックス状態：最終更新、文書数、チャンク数、エラー数
* 「インデックス作成」「再インデックス」ボタン
* エラー一覧（ファイルパス＋理由）

2. **Search（検索）**

* 検索欄
* タブ：`Semantic` / `Keyword` / `Hybrid`（Hybridは結果を統合して表示）
* 根拠カード一覧（クリックでプレビュー）

3. **Ask（質問）**

* 質問欄
* 回答（箇条書き中心）
* 根拠（Top5〜10）表示（クリックでプレビュー）

---

## データモデル（SQLite）

### documents

* `id` (uuid)
* `path` (unique)
* `title`
* `ext`
* `mtime`
* `size`
* `status` (`indexed` / `error` / `pending`)

### chunks

* `id`
* `document_id`
* `page` (pdf only, nullable)
* `start_offset` / `end_offset`（または snippet anchor）
* `text`
* `hash`（重複検出）

### embeddings

* `chunk_id`
* `vector_id`（FAISSなら整数IDなど）
* `model_name`
* `created_at`

### index_jobs

* `id`
* `target_path`
* `started_at` / `finished_at`
* `total` / `done` / `error_count`
* `log`（簡易）

### settings

* `included_paths`（JSON）
* `allowed_ext`（JSON）
* `embedding_model`
* `generation_mode`（none/local/cloud）

---

## 主要モジュール（内部構成）

* `Ingestion`: フォルダ走査、ファイル列挙
* `Extractor`: pdf/txt/md → テキスト（PDFはページ番号保持）
* `Chunker`: テキスト→チャンク（見出し保持は後でも可）
* `Embedder`: chunk→embedding（ローカル）
* `IndexStore`: SQLite保存、FTS更新、FAISS index更新
* `Retriever`: keyword検索 / semantic検索 / hybrid統合
* `Answerer`: 生成なし要約 or LLMで回答（根拠必須）
* `UI`: Library/Search/Ask

---

## ハイブリッド検索の仕様（MVP版）

* semantic TopK（例：K=20）
* keyword TopK（例：K=20）
* 統合：重複排除 → スコア正規化（簡易でOK）→ 上位N（例：N=10）を根拠として採用

---

## Definition of Done（完成判定）

* 指定フォルダ（PDF 100〜300本程度）をインデックスできる
* Searchで keyword/semantic の両方が動く
* Askで回答＋根拠カードが必ず表示される
* エラーがUIで確認できる（黙って落ちない）
* 生成なしモードでも成立（完全ローカル動作）

---

## 実装順（安全に積む）

1. Library：フォルダ追加→ファイル一覧
2. Extractor：txt/md/pdf抽出→documents登録
3. Chunker：chunks保存（この時点でプレビュー可）
4. FTS5：keyword検索を先に完成
5. Embedder＋FAISS：semantic検索を追加
6. Hybrid統合＋ランキング
7. Ask：根拠カード中心→生成なし要約→（任意で生成モード追加）
8. Index Jobs：進捗・エラー表示の仕上げ

---

## Technical stack

1. Back end: Python 
2. UI: PySide6
3. LLM: Cloud OpenAI api
