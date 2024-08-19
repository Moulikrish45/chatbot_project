document.getElementById("send-btn").addEventListener("click", function() {
    const userInput = document.getElementById("user-input").value;
    if (userInput) {
        addMessageToChat("You", userInput);
        sendMessageToBot(userInput);
        document.getElementById("user-input").value = "";
    }
});

function addMessageToChat(sender, message) {
    const output = document.getElementById("output");
    const newMessage = document.createElement("p");
    newMessage.innerHTML = `<strong>${sender}:</strong> ${message}`;
    output.appendChild(newMessage);
    output.scrollTop = output.scrollHeight;
}

function sendMessageToBot(message) {
    fetch("/chatbot", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => addMessageToChat("Bot", data.message))
    .catch(error => console.error("Error:", error));
}
