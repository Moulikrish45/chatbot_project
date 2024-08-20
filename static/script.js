document.getElementById("send-btn").addEventListener("click", function() {
    const userInput = document.getElementById("user-input").value;
    if (userInput) {
        addMessageToChat("You", userInput);
        sendMessageToBot(userInput);
        document.getElementById("user-input").value = "";
    }
});

document.getElementById("upload-btn").addEventListener("click", function() {
    document.getElementById("image-upload").click();
});

document.getElementById("image-upload").addEventListener("change", function() {
    const file = this.files[0];
    if (file) {
        uploadImage(file);
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
    .then(data => {
        addMessageToChat("Bot", data.message);
        if (data.options) {
            displayOptions(data.options);
        } else if (data.contractors) {
            displayContractors(data.contractors, data.example);
        }
    })
    .catch(error => console.error("Error:", error));
}

function uploadImage(file) {
    const formData = new FormData();
    formData.append('file', file);

    fetch("/upload_image", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        addMessageToChat("Bot", data.message);
        if (data.options) {
            displayOptions(data.options);
        }
    })
    .catch(error => console.error("Error:", error));
}

function displayOptions(options) {
    const output = document.getElementById("output");
    const optionsContainer = document.createElement("div");
    optionsContainer.classList.add("options-container");

    options.forEach(option => {
        const button = document.createElement("button");
        button.innerText = option;
        button.classList.add("option-button");
        button.addEventListener("click", function() {
            addMessageToChat("You", option);
            sendMessageToBot(option);
        });
        optionsContainer.appendChild(button);
    });

    output.appendChild(optionsContainer);
    output.scrollTop = output.scrollHeight;
}

function displayContractors(contractors, example) {
    const output = document.getElementById("output");
    const contractorsContainer = document.createElement("div");
    contractorsContainer.classList.add("contractors-container");

    contractors.forEach(contractor => {
        const contractorItem = document.createElement("p");
        contractorItem.innerText = contractor;
        contractorsContainer.appendChild(contractorItem);
    });

    const exampleText = document.createElement("p");
    exampleText.innerText = `Example: ${example}`;
    contractorsContainer.appendChild(exampleText);

    output.appendChild(contractorsContainer);
    output.scrollTop = output.scrollHeight;
}
