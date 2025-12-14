"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {

    const [userId, setUserId] = useState("");
    const router = useRouter();

    const handleLogin = () => {
        if(!userId)
            return;
        localStorage.setItem("userId", userId);
        router.push("/learn");
    }

    return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="bg-white p-8 rounded shadow w-96">
        <h2 className="text-2xl font-bold mb-4">Login / Signup</h2>

        <input
          className="border w-full p-2 mb-4"
          placeholder="Enter your user_id"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
        />

        <button
          onClick={handleLogin}
          className="w-full bg-black text-white py-2 rounded"
        >
          Continue
        </button>
      </div>
    </div>
  );
}