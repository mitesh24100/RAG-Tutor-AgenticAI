const BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL!;

export async function startLesson (userId: string, topic: string) {
    const result = await fetch(`${BASE_URL}/start_lesson`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ user_id: userId, topic }),
    });
    return result.json();
}

export async function submitAnswer (userId: string, topic: string, answer: string) {
    const result = await fetch(`${BASE_URL}/submit`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ user_id: userId, topic, answer }),
    });
    return result.json();
}

export async function continueLesson (userId: string, topic: string) {
    const result = await fetch(`${BASE_URL}/continue_lesson`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ user_id: userId, topic }),
    });
    return result.json();
}