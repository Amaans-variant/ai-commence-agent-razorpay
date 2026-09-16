import { fetchChat } from './api.js';
import { appendMessage, scrollToBottom } from './chat.js';
import { renderStage } from './stage.js';

document.addEventListener("DOMContentLoaded", () => {
    const sendBtn = document.getElementById("send-btn");
    const inputField = document.getElementById("user-input");

    if (sendBtn) {
        sendBtn.addEventListener("click", sendMessage);
    }
    
    if (inputField) {
        inputField.addEventListener("keypress", (event) => {
            if (event.key === "Enter") {
                sendMessage();
            }
        });
    }
});

async function sendMessage() {
    const inputField = document.getElementById("user-input");
    if (!inputField) return;
    
    const messageText = inputField.value.trim();
    if (!messageText) return;

    appendMessage(messageText, "user-msg");
    inputField.value = "";
    scrollToBottom();

    try {
        const response = await fetchChat(messageText);
        handleResponse(response);
    } catch (error) {
        console.error("Connection Error:", error); 
        appendMessage("Error connecting to the server.", "ai-msg");
    }
}

function handleResponse(response) {
    if (response.message) {
        appendMessage(response.message, "ai-msg");
    }
    renderStage(response);
}
