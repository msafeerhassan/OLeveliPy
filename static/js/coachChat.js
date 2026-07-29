document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("chatForm");
    const input = document.getElementById("chatInput");
    const msgContainer = document.getElementById("chatMessages");

    if (window.prefillMessage) {
        input.value = window.prefillMessage;
        form.dispatchEvent(new Event("submit"));
    }

    function appendMsg(role, content) {
        const div = document.createElement("div");
        div.className = `chat-message chat-${role}`;

        const label = document.createElement("strong");
        if (role === "user") {
            label.textContent = "You: ";
        }
        else {
            label.textContent = "Coach: ";
        }

        div.appendChild(label);
        div.appendChild(document.createTextNode(content));

        msgContainer.appendChild(div);
        msgContainer.scrollTop = msgContainer.scrollHeight;
    }

    form.addEventListener("submit", async function (event) {
        event.preventDefault();

        const msg = input.value.trim();

        if (!msg) {
            return ;
        }

        appendMsg("user", msg);
        input.value = "";
        input.disabled = true;

        let response;
        try {
            response = await fetch("/api/coach-chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(
                    {
                        message: msg,
                        aboutEntryId: window.aboutEntryId || null
                    }
                )
            });
        } catch (err) {
            appendMsg("assistant", `Error: ${err}`);
            input.disabled = false;
            return ;
        }

        let data;

        try {
            data = await response.json();
        } catch (error) {
            appendMsg("assistant", `Failed to parse response (status ${response.status}): ${error}`);
            input.disabled = false;
            return ;
        }

        if (!data.status) {
            appendMsg("assistant", `Error: ${data.result}`);
        } else {
            appendMsg("assistant", data.result);
        }

        input.disabled = false;
        input.focus();
    });
});