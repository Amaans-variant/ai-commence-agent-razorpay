export function appendMessage(text, className) {
    const msgDiv = document.createElement("div");
    msgDiv.className = "msg " + className;
    msgDiv.innerText = text;
    
    const messagesContainer = document.getElementById("messages");
    if (messagesContainer) {
        messagesContainer.appendChild(msgDiv);
    }
    scrollToBottom();
}

export function scrollToBottom() {
    const messagesDiv = document.getElementById("messages");
    if (messagesDiv) {
        messagesDiv.scrollTo({
            top: messagesDiv.scrollHeight,
            behavior: 'smooth'
        });
    }
}
