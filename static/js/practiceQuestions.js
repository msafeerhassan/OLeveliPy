document.addEventListener("DOMContentLoaded", function () {
    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text == null ? "" : String(text);
        return div.innerHTML;
    }

    const genForm = document.getElementById("generateForm");
    const genStatus = document.getElementById("generateStatus");

    genForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const subjectName = document.getElementById("subjectName").value;
        const subjectCode = document.getElementById("subjectCode").value;
        const topic = document.getElementById("topic").value;

        genStatus.textContent = "Generating Question...";

        let response;
        try {
            response = await fetch("/api/generate-practice-question", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(
                    {
                        subjectName: subjectName,
                        subjectCode: subjectCode,
                        topic: topic
                    }
                )
            });
        } catch (err) {
            genStatus.textContent = "Failed: " + err;
            return ;
        }

        const data = await response.json();

        if (!data.status) {
            genStatus.textContent = "Failed: " + data.result;
            return;
        }

        genStatus.textContent = "Question Generated. Reloading...";
        window.location.reload();
    });

    document.querySelectorAll(".gradeForm").forEach(function (form) {
        form.addEventListener("submit", async function (event) {
            event.preventDefault();

            const container = form.closest(".practice-question");
            const questionId = form.querySelector(".questionIdInput").value;
            const answerText = form.querySelector(".answerTextInput").value.trim();
            const files = form.querySelector(".answerImageInput").files;
            const resultDiv = container.querySelector(".gradeResult");

            if (!answerText && files.length === 0) {
                resultDiv.textContent = "Please type an answer or upload an image."
                return ;
            }

            const formData = new FormData();

            formData.append("questionId", questionId);

            if (answerText) {
                formData.append("answerText", answerText)
            } else {
                for (let i = 0; i < files.length; i++) {
                    formData.append("answerImages", files[i]);    
                }
            }

            resultDiv.textContent = "Grading...";

            let response;
            try {
                response = await fetch("/api/grade-practice-question", {
                    method: "POST",
                    body: formData
                });
            } catch (err) {
                resultDiv.textContent = "Failed: " + err;
                return;
            }

            const data = await response.json();

            if (!data.status) {
                resultDiv.textContent = "Failed: " + escapeHtml(data.result);
                return;
            }

            const result = data.result;
            resultDiv.innerHTML = `<p><strong>Score: ${escapeHtml(result.marks_awarded)}/${escapeHtml(result.marks_total)}</strong></p><p>${escapeHtml(result.overall_feedback)}</p>`;
        });
    });
});