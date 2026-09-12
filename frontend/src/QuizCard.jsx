import { useState } from "react";

function Question({ item, index }) {
  const [picked, setPicked] = useState(null);

  function choose(optionIndex) {
    if (picked !== null) return;
    setPicked(optionIndex);
  }

  function optionClass(optionIndex) {
    if (picked === null) {
      return "option";
    }

    if (optionIndex === item.correct_index) {
      return "option is-correct";
    }

    if (optionIndex === picked) {
      return "option is-wrong";
    }

    return "option is-muted";
  }

  const difficulty =
    item.difficulty?.toLowerCase() || "medium";

  const result =
    picked === null
      ? null
      : picked === item.correct_index
        ? "Correct."
        : "Not quite.";

  return (
    <li className="question">
      <div className="question-meta">
        <span className="question-number">
          {String(index + 1).padStart(2, "0")}
        </span>

        <span
          className={`difficulty difficulty-${difficulty}`}
        >
          {difficulty}
        </span>
      </div>

      <h3 className="question-text">
        {item.question}
      </h3>

      <div className="options">
        {item.options.map((option, optionIndex) => (
          <button
            key={optionIndex}
            type="button"
            className={optionClass(optionIndex)}
            onClick={() => choose(optionIndex)}
            disabled={picked !== null}
          >
            <span className="option-letter">
              {String.fromCharCode(65 + optionIndex)}
            </span>

            <span>{option}</span>
          </button>
        ))}
      </div>

      {picked !== null && (
        <div className="explanation">
          <strong>{result}</strong>
          <span>{item.explanation}</span>
        </div>
      )}
    </li>
  );
}

export default function QuizCard({ set }) {
  if (!set) {
    return null;
  }

  const questions = Array.isArray(set.questions)
    ? set.questions
    : [];

  return (
    <article className="card">
      <section className="summary-section">
        <p className="section-label">
          SUMMARY
        </p>

        <p className="summary">
          {set.summary}
        </p>
      </section>

      <section className="questions-section">
        <div className="questions-heading">
          <p className="section-label">
            QUESTIONS
          </p>

          <span className="question-count">
            {questions.length} questions
          </span>
        </div>

        <ol className="questions">
          {questions.map((item, index) => (
            <Question
              key={index}
              item={item}
              index={index}
            />
          ))}
        </ol>
      </section>
    </article>
  );
}