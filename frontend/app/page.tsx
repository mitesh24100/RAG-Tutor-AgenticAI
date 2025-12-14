import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center">
      <h1 className="text-4xl font-bold mb-4">AI Tutor</h1>
      <p className="mb-6 text-gray-600">
        Learn anything with an agentic AI tutor
      </p>
      <Link
        href="/login"
        className="px-6 py-3 bg-black text-white rounded"
      >
        Get Started
      </Link>
    </main>
  );
}
