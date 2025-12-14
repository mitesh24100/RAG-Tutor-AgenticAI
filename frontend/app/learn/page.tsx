"use client";

import { useEffect, useState } from "react";
import {
  startLesson,
  submitAnswer,
  continueLesson,
} from "@/lib/api";

export default function LearnPage() {
    const [topic, setTopic] = useState("Baseball");
    const [lesson, setLesson] = useState<any>(null);
    const [answer, setAnswer] = useState("");
    const [feedback, setFeedback] = useState<any>(null);

    const userId = typeof window !== "undefined" ? localStorage.getItem("userId") : null;

    useEffect(
        () => {
            if (!userId) return;
            startLesson(userId, topic).then(setLesson);
        }, []
    );

    const handleSubmit = async () => {
        if(!userId) return;

        const result = await submitAnswer(userId, topic, answer);
        setFeedback(result);
    };

    const handleContinue = async () => {
        if (!userId) return;

        const result = await continueLesson(userId, topic);
        setLesson(result);
        setAnswer("");
        setFeedback(null);
    };

    if (!lesson)
        return (
        <div className="min-h-screen flex items-center justify-center">
            <p>Loading lesson...</p>
        </div>
    );

    return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">
        {lesson.lesson_title}
      </h1>

      <p className="mb-6 whitespace-pre-wrap">
        {lesson.tutorial}
      </p>

      <div className="mb-4 font-semibold">
        {lesson.question}
      </div>

      <textarea
        className="border w-full p-2 mb-4"
        rows={3}
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
      />

      <button
        onClick={handleSubmit}
        className="bg-black text-white px-4 py-2 rounded mr-2"
      >
        Submit Answer
      </button>

      <button
        onClick={handleContinue}
        className="bg-gray-300 px-4 py-2 rounded"
      >
        Continue
      </button>

      {feedback && (
        <div className="mt-6 p-4 border rounded">
          <p>
            <strong>Mastery:</strong> {feedback.mastery}
          </p>
          <p>{feedback.feedback}</p>
        </div>
      )}
    </div>
  );
}