import { useEffect, useRef, useState } from "react";
import {
  SignedIn,
  SignedOut,
  SignIn,
  UserButton,
  useUser,
} from "@clerk/clerk-react";

import QuizCard from "./QuizCard";
import { useApi } from "./api";

const MIN_CHARS = 100;
const MAX_PDF_SIZE = 10 * 1024 * 1024;

export default function App() {
  const { generateSet, generatePdf, fetchHistory, wakeServer } = useApi();
  const { user } = useUser();

  const fileInputRef = useRef(null);

  const [tab, setTab] = useState("create");
  const [inputMode, setInputMode] = useState("text");
  const [notes, setNotes] = useState("");
  const [pdfFile, setPdfFile] = useState(null);
  const [current, setCurrent] = useState(null);
  const [history, setHistory] = useState([]);
  const [status, setStatus] = useState("waking");
  const [error, setError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    wakeServer()
      .then(() => setStatus("idle"))
      .catch(() => setStatus("idle"));
  }, []);

  useEffect(() => {
    if (tab !== "history") return;

    fetchHistory()
      .then((data) => setHistory(data.items))
      .catch((err) => setError(err.message));
  }, [tab]);

  function validatePdf(file) {
    if (!file) return false;

    if (file.type !== "application/pdf") {
      setError("Please choose a PDF file.");
      return false;
    }

    if (file.size > MAX_PDF_SIZE) {
      setError("PDF is too large. Maximum size is 10 MB.");
      return false;
    }

    setError(null);
    return true;
  }

  function handleFileSelect(file) {
    if (!validatePdf(file)) return;

    setPdfFile(file);
    setInputMode("pdf");
    setCurrent(null);
  }

  function handleFileInput(event) {
    const file = event.target.files?.[0];

    if (file) {
      handleFileSelect(file);
    }

    event.target.value = "";
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);

    const file = event.dataTransfer.files?.[0];

    if (file) {
      handleFileSelect(file);
    }
  }

  function handleDragOver(event) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(event) {
    event.preventDefault();
    setIsDragging(false);
  }

  function removePdf() {
    setPdfFile(null);
    setError(null);
    setCurrent(null);
  }

  async function handleGenerate() {
    setStatus("working");
    setError(null);
    setCurrent(null);

    try {
      let data;

      if (inputMode === "pdf") {
        if (!pdfFile) {
          throw new Error("Please choose a PDF first.");
        }

        data = await generatePdf(pdfFile);
      } else {
        if (notes.trim().length < MIN_CHARS) {
          throw new Error(
            `Please enter at least ${MIN_CHARS} characters of notes.`
          );
        }

        data = await generateSet(notes);
      }

      setCurrent(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setStatus("idle");
    }
  }

  const tooShort = notes.trim().length < MIN_CHARS;

  const canGenerate =
    status === "idle" &&
    (inputMode === "text" ? !tooShort : pdfFile !== null);

  function switchInputMode(mode) {
    setInputMode(mode);
    setError(null);
    setCurrent(null);
  }

  const userEmail = user?.primaryEmailAddress?.emailAddress;

  return (
    <main className="app">
      {/* =====================================================
          Header
          ===================================================== */}

      <header className="masthead">
        <div>
          <p className="eyebrow">A study tool</p>

          <h1>Notes to quiz</h1>

          <p className="masthead-description">
            Turn your study material into a summary and questions
            that get harder as you go.
          </p>
        </div>

        <SignedIn>
          <UserButton />
        </SignedIn>
      </header>

      {/* =====================================================
          Signed out
          ===================================================== */}

      <SignedOut>
        <section className="signin">
          <p className="notice">
            Sign in to generate and save quizzes.
          </p>

          <SignIn routing="hash" />
        </section>
      </SignedOut>

      {/* =====================================================
          Signed in
          ===================================================== */}

      <SignedIn>
        <div className="account-line">
          <span>Signed in as</span>
          <strong>{userEmail}</strong>
        </div>

        {/* Main navigation */}
        <div className="create-intro">
          <div>
            <h2>What are you studying?</h2>
          </div>
          <p>
            Paste your notes or bring in a PDF. We'll turn them
            into a revision set.
          </p>
        </div>

        <nav className="tabs">
          <button
            className={tab === "create" ? "tab is-active" : "tab"}
            onClick={() => {
              setTab("create");
              setError(null);
            }}
          >
            Create
          </button>

          <button
            className={tab === "history" ? "tab is-active" : "tab"}
            onClick={() => {
              setTab("history");
              setError(null);
            }}
          >
            Saved
          </button>
        </nav>

        {status === "waking" && (
          <p className="notice">
            Waking the server up. This takes up to a minute on the free plan.
          </p>
        )}

        {error && (
          <p className="notice is-error">
            {error}
          </p>
        )}

        {/* ===================================================
            CREATE
            =================================================== */}

        {tab === "create" && (
          <section className="create-section">

            <div className="create-heading">
              <div>
                <p className="section-kicker">New study set</p>

                <h2>What are you studying?</h2>
              </div>

              <p>
                Paste your notes or bring in a PDF. We'll turn
                them into a revision set.
              </p>
            </div>

            {/* Input method switch */}

            <div className="source-switch" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={inputMode === "text"}
                className={
                  inputMode === "text"
                    ? "source-button is-active"
                    : "source-button"
                }
                onClick={() => switchInputMode("text")}
              >
                <span className="source-number">01</span>
                <span>
                  <strong>Paste notes</strong>
                  <small>Write or paste text</small>
                </span>
              </button>

              <button
                type="button"
                role="tab"
                aria-selected={inputMode === "pdf"}
                className={
                  inputMode === "pdf"
                    ? "source-button is-active"
                    : "source-button"
                }
                onClick={() => switchInputMode("pdf")}
              >
                <span className="source-number">02</span>
                <span>
                  <strong>Upload PDF</strong>
                  <small>Use a study document</small>
                </span>
              </button>
            </div>

            {/* =================================================
                Text workspace
                ================================================= */}

            {inputMode === "text" && (
              <div className="study-workspace">

                <div className="workspace-label">
                  <span>Your notes</span>
                  <span>Minimum {MIN_CHARS} characters</span>
                </div>

                <textarea
                  value={notes}
                  onChange={(e) => {
                    setNotes(e.target.value);
                    setCurrent(null);
                  }}
                  placeholder={
                    "Paste a paragraph, lecture notes, textbook excerpt,\n" +
                    "or anything else you want to revise..."
                  }
                  rows={12}
                />

                <div className="workspace-footer">
                  <div className="input-meta">
                    <span>
                      {notes.trim().length.toLocaleString()} characters
                    </span>

                    {tooShort && (
                      <span className="input-warning">
                        {MIN_CHARS - notes.trim().length} more needed
                      </span>
                    )}
                  </div>

                  <button
                    className="generate-button"
                    onClick={handleGenerate}
                    disabled={!canGenerate}
                  >
                    <span>
                      {status === "working"
                        ? "Building study set..."
                        : "Generate study set"}
                    </span>

                    {status !== "working" && (
                      <span className="button-arrow">→</span>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* =================================================
                PDF workspace
                ================================================= */}

            {inputMode === "pdf" && (
              <div className="study-workspace pdf-workspace">

                <div className="workspace-label">
                  <span>Study document</span>
                  <span>PDF · Maximum 10 MB</span>
                </div>

                {!pdfFile ? (
                  <div
                    className={
                      isDragging
                        ? "pdf-dropzone is-dragging"
                        : "pdf-dropzone"
                    }
                    onClick={() => fileInputRef.current?.click()}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="application/pdf,.pdf"
                      onChange={handleFileInput}
                      hidden
                    />

                    <div className="pdf-mark">PDF</div>

                    <div className="pdf-drop-copy">
                      <strong>Drop your study material here</strong>
                      <span>
                        or click to choose a PDF from your computer
                      </span>
                    </div>

                    <span className="pdf-browse">
                      Browse files →
                    </span>
                  </div>
                ) : (
                  <div className="selected-file">

                    <div className="file-symbol">PDF</div>

                    <div className="file-details">
                      <strong>{pdfFile.name}</strong>

                      <span>
                        {(pdfFile.size / (1024 * 1024)).toFixed(2)} MB
                      </span>
                    </div>

                    <button
                      type="button"
                      className="remove-file"
                      onClick={removePdf}
                    >
                      Remove
                    </button>
                  </div>
                )}

                <div className="workspace-footer">
                  <div className="input-meta">
                    <span>
                      {pdfFile
                        ? "Document ready"
                        : "Choose a PDF to continue"}
                    </span>
                  </div>

                  <button
                    className="generate-button"
                    onClick={handleGenerate}
                    disabled={!canGenerate}
                  >
                    <span>
                      {status === "working"
                        ? "Building study set..."
                        : "Generate study set"}
                    </span>

                    {status !== "working" && (
                      <span className="button-arrow">→</span>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Generated result */}

            {current && (
              <div className="generated-area">
                <div className="generated-heading">
                  <span className="section-kicker">
                    Study set ready
                  </span>

                  <span>
                    10 questions · increasing difficulty
                  </span>
                </div>

                <QuizCard set={current} />
              </div>
            )}
          </section>
        )}

        {/* ===================================================
            SAVED
            =================================================== */}

        {tab === "history" && (
          <section className="history-section">

            <div className="create-heading">
              <div>
                <p className="section-kicker">Your library</p>
                <h2>Saved study sets</h2>
              </div>

              <p>
                Revisit quizzes you've already generated.
              </p>
            </div>

            {history.length === 0 ? (
              <p className="notice">
                Nothing saved yet. Generate a quiz first.
              </p>
            ) : (
              history.map((set) => (
                <QuizCard key={set.id} set={set} />
              ))
            )}
          </section>
        )}
      </SignedIn>
    </main>
  );
}