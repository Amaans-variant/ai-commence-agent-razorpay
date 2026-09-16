export const currentSessionId = "user_" + Math.random().toString(36).substring(7);
export const API_URL = window.location.origin;

export async function fetchChat(messageText) {
    const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
            message: messageText, 
            session_id: currentSessionId 
        })
    });
    return await response.json();
}

export async function fetchPaymentStatus(link) {
    const response = await fetch(`${API_URL}/status?url=${encodeURIComponent(link)}`);
    return await response.json();
}
