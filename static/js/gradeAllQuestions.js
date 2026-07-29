document.addEventListener("DOMContentLoaded", function() {
    const form = document.getElementById("pastPaperExaminerForm");
    const progressStatus = document.getElementById("progressStatus");
    const resultsContainer = document.getElementById("allQuestionsResults");

    form.addEventListener("submit", async function (event) {
        const questionScope = form.querySelector('input[name="questionScope"]:checked').value;

        if (questionScope !== "all") {
            return;
        }

        event.preventDefault();

        progressStatus.textContent = "Uploading Images and Identifying Questions...";
        resultsContainer.innerHTML = "";

        const formData = new FormData(form);

        let submitResponse;

        try {
            submitResponse = await fetch("/past-paper-checker/submit", {
                method: "POST",
                body: formData
            });
        } catch (err) {
            progressStatus.textContent = "Failed to Submit: " + err;
            return;
        }

        const rawResponseText = await submitResponse.text();

        let submitData;

        try {
            submitData = JSON.parse(rawResponseText)
        } catch (err) {
            console.log("RAW SERVER RESPONSE:", rawResponseText)
            progressStatus.textContent = `Failed to parse server response (status ${submitResponse.status}): ${err}`;
            return;
        }

        if (!submitData.status) {
            progressStatus.textContent = "Failed: " + submitData.result;
            return;
        }

        const segments = submitData.segments;
        const imagePaths = submitData.imagePaths;

        for (let i = 0; i < segments.length; i++) {
            const segment = segments[i];
            progressStatus.textContent = `Grading Question ${segment.question_number} (${i + 1} of ${segments.length})...`;

            const segmentImagePaths = segment.image_indices.map(function (index) {
                return imagePaths[index];
            });

            let gradeResponse;

            try {
                gradeResponse = await fetch("/api/grade-question", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        subjectName: submitData.subjectName,
                        subjectCode: submitData.subjectCode,
                        examinationYear: submitData.examinationYear,
                        examinationSeries: submitData.examinationSeries,
                        variant: submitData.variant,
                        questionNumber: segment.question_number,
                        markSchemePath: submitData.markSchemePath,
                        answerImagesPath: segmentImagePaths
                    })
                });
            } catch (err) {
                resultsContainer.innerHTML += `<p>Question ${segment.question_number}: request failed (${err})</p>`;
                continue;
            }

            const gradeData = await gradeResponse.json();

            if (!gradeData.status) {
                resultsContainer.innerHTML += `<p>Question ${segment.question_number}: grading failed (${gradeData.result})</p>`;
                continue;
            }

            const result = gradeData.result;

            resultsContainer.innerHTML += `
            <div>
                <h3>Question ${segment.question_number}: ${result.marks_awarded} / ${result.marks_total}</h3>
                <p>${result.overall_feedback}</p>
            </div>
            `;
        }

        progressStatus.textContent = "Done!";
    });
});